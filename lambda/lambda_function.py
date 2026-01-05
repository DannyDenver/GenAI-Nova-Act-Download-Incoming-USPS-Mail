#!/usr/bin/env python3
"""
AWS Lambda function for USPS Informed Delivery automation.
Main orchestration module that coordinates all components.
"""

import os
import json
import boto3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import our custom modules
from utils import USPSAuthenticator, MailImageExtractor, S3Uploader, NovaActConfig

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class LambdaUSPSAutomator:
    """Main Lambda automation orchestrator."""
    
    def __init__(self, s3_bucket: str, secret_name: str, aws_region: str):
        self.s3_bucket = s3_bucket
        self.secret_name = secret_name
        self.aws_region = aws_region
        self.today = datetime.now().strftime("%Y-%m-%d")
        
        # Initialize AWS clients
        self.secrets_client = boto3.client('secretsmanager', region_name=aws_region)
        
        # Get credentials from Secrets Manager
        self.username, self.password = self._get_credentials()
        
        # Initialize components
        self.s3_uploader = S3Uploader(s3_bucket, aws_region)
        self.nova_act_config = NovaActConfig("/tmp/nova_act_logs")
        
        # Will be initialized later
        self.authenticator: Optional[USPSAuthenticator] = None
        self.image_extractor: Optional[MailImageExtractor] = None
    
    def _get_credentials(self) -> tuple[str, str]:
        """Retrieve USPS credentials from AWS Secrets Manager."""
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            secret_data = json.loads(response['SecretString'])
            return secret_data['username'], secret_data['password']
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            raise
    
    def _upload_callback(self, file_data: bytes, filename: str) -> bool:
        """Callback function for image uploads."""
        return self.s3_uploader.upload_file(file_data, filename)
    
    def run(self) -> Dict[str, Any]:
        """Run the automation and return results."""
        start_time = datetime.now()
        uploaded_files = []        
        uploaded_logs = []
        success = False
        error_message = None
        method = "nova_act"
        nova_act = None
        
        try:
            logger.info("Starting USPS Lambda automation with Nova Act...")
            
            # Initialize Nova Act
            nova_act = self.nova_act_config.initialize()
            
            # Initialize components with Nova Act instance
            self.authenticator = USPSAuthenticator(nova_act, self.username, self.password)
            self.image_extractor = MailImageExtractor(nova_act, self._upload_callback)
            
            # Execute automation workflow
            self.authenticator.start_and_navigate()
            
            if self.authenticator.attempt_login():
                logger.info("Login successful, proceeding...")
                
                if self.authenticator.find_informed_delivery():
                    logger.info("Found Informed Delivery, checking for mail...")
                    
                    # Extract images and fix S3 paths
                    raw_files = self.image_extractor.check_mail_images()
                    uploaded_files = [f.replace("s3://bucket/", f"s3://{self.s3_bucket}/") for f in raw_files if f]
                    
                    success = True
                else:
                    error_message = "Could not access Informed Delivery"
                    logger.warning(error_message)
            else:
                error_message = "Login failed"
                logger.error(error_message)
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"Nova Act automation failed: {e}")
        
        finally:
            # Stop Nova Act session
            if nova_act:
                self.nova_act_config.stop()
            
            # Upload logs to S3 (if enabled)
            upload_logs = os.environ.get('UPLOAD_LOGS_TO_S3', 'true').lower() == 'true'
            if upload_logs:
                try:
                    logger.info("Uploading Nova Act logs to S3...")
                    uploaded_logs = self.s3_uploader.upload_logs(self.nova_act_config.logs_dir)
                except Exception as e:
                    logger.error(f"Failed to upload logs: {e}")
            else:
                logger.info("Log upload to S3 disabled via UPLOAD_LOGS_TO_S3 environment variable")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "success": success,
            "images_downloaded": len(uploaded_files),
            "s3_uploads": len(uploaded_files),
            "uploaded_files": uploaded_files,
            "uploaded_logs": uploaded_logs,
            "logs_uploaded": len(uploaded_logs),
            "execution_time": execution_time,
            "date": self.today,
            "method": method,
            "error_message": error_message
        }


def lambda_handler(event, context):
    """AWS Lambda handler function."""
    logger.info(f"Lambda function started. Event: {json.dumps(event)}")
    
    # Get environment variables
    s3_bucket = os.environ.get('S3_BUCKET_NAME')
    secret_name = os.environ.get('SECRET_NAME')
    aws_region = os.environ.get('AWS_REGION', 'us-east-1')
    
    if not s3_bucket or not secret_name:
        error_msg = "Missing required environment variables: S3_BUCKET_NAME, SECRET_NAME"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': error_msg
            })
        }
    
    try:
        # Create and run automator
        automator = LambdaUSPSAutomator(s3_bucket, secret_name, aws_region)
        result = automator.run()
        
        # Log results
        logger.info(f"Automation completed: {json.dumps(result)}")
        
        # Return response
        status_code = 200 if result['success'] else 500
        return {
            'statusCode': status_code,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        error_msg = f"Lambda execution failed: {str(e)}"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': error_msg
            })
        }