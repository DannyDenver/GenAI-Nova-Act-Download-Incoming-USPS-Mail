#!/usr/bin/env python3
"""
AWS Lambda function for USPS Informed Delivery automation.
Adapted from the conservative USPS automation script.
"""

import os
import json
import boto3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import requests
from urllib.parse import urljoin

from nova_act import NovaAct
from nova_act.types.act_result import ActResult
from nova_act.types.act_errors import ActAgentError, ActClientError, ActExecutionError, ActServerError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class LambdaUSPSAutomator:
    """Lambda-compatible USPS automation class."""
    
    def __init__(self, s3_bucket: str, secret_name: str, aws_region: str):
        self.s3_bucket = s3_bucket
        self.secret_name = secret_name
        self.aws_region = aws_region
        self.nova_act: Optional[NovaAct] = None
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=aws_region)
        self.secrets_client = boto3.client('secretsmanager', region_name=aws_region)
        
        # Get credentials from Secrets Manager
        self.username, self.password = self._get_credentials()
        
        # Create date-based folder structure
        self.today = datetime.now().strftime("%Y-%m-%d")
    
    def _get_credentials(self) -> tuple[str, str]:
        """Retrieve USPS credentials from AWS Secrets Manager."""
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            secret_data = json.loads(response['SecretString'])
            return secret_data['username'], secret_data['password']
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            raise
    
    def _upload_to_s3(self, file_data: bytes, filename: str, content_type: str = 'image/png') -> bool:
        """Upload file data to S3 with retry logic."""
        s3_key = f"{self.today}/{filename}"
        
        for attempt in range(3):  # Retry up to 3 times
            try:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=file_data,
                    ContentType=content_type,
                    Metadata={
                        'download-date': self.today,
                        'source': 'usps-informed-delivery',
                        'automation-version': '1.0'
                    }
                )
                logger.info(f"✓ Uploaded to S3: {s3_key}")
                return True
            except Exception as e:
                logger.warning(f"S3 upload attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    logger.error(f"Failed to upload {filename} after 3 attempts")
                    return False
        return False
    
    def initialize_nova_act(self) -> None:
        """Initialize Nova Act for Lambda environment."""
        try:
            # Create logs directory in Lambda's tmp space
            logs_dir = "/tmp/nova_act_logs"
            os.makedirs(logs_dir, exist_ok=True)
            
            # Set environment variables for Microsoft Playwright image
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/ms-playwright'
            os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'
            os.environ['NOVA_ACT_SKIP_PLAYWRIGHT_INSTALL'] = '1'
            
            # Log environment info for debugging
            logger.info(f"Python version: {os.sys.version}")
            logger.info(f"PLAYWRIGHT_BROWSERS_PATH: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
            logger.info(f"Available files in /ms-playwright: {os.listdir('/ms-playwright') if os.path.exists('/ms-playwright') else 'Directory not found'}")
            
            # Check for Chromium executable
            chromium_paths = [
                '/ms-playwright/chromium-*/chrome-linux/chrome',
                '/ms-playwright/chromium-*/chrome-linux/headless_shell',
                '/ms-playwright/chromium*/chrome-linux/chrome',
                '/ms-playwright/chromium*/chrome-linux/headless_shell'
            ]
            
            import glob
            for pattern in chromium_paths:
                matches = glob.glob(pattern)
                if matches:
                    logger.info(f"Found Chromium executable(s): {matches}")
                    break
            else:
                logger.warning("No Chromium executable found in expected locations")
            
            logger.info("Attempting Nova Act initialization with Microsoft Playwright image...")
            
            # Try Nova Act with minimal configuration - remove security_options that's causing issues
            self.nova_act = NovaAct(
                starting_page="https://www.usps.com/",
                headless=True,  # Always headless in Lambda
                logs_directory=logs_dir,  # Use Lambda's tmp directory
                clone_user_data_dir=False,  # Don't clone user data in Lambda
                go_to_url_timeout=60,
                nova_act_api_key=os.environ.get("NOVA_ACT_API_KEY"),
                chrome_channel="chromium"
            )
            logger.info("Nova Act initialized successfully for Lambda")
                
        except Exception as e:
            logger.error(f"Failed to initialize Nova Act: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def start_and_navigate(self) -> None:
        """Start session and navigate to login."""
        try:
            self.nova_act.start()
            logger.info("Nova Act session started")
            
            # Navigate to sign in
            account_search = self.nova_act.act(
                "I need to access my personal USPS account to check my mail. "
                "Click on the 'sign in' button on the top right of the main page."
            )
            logger.info(f"Navigation result: {account_search}")
            
        except Exception as e:
            logger.error(f"Failed to start and navigate: {e}")
            raise
    
    def attempt_login(self) -> bool:
        """Attempt to login with credentials."""
        try:
            self.nova_act.page.wait_for_timeout(3000)
            
            # Find and focus username field
            username_field = self.nova_act.act("Find the username input field and click on it to focus it.")
            logger.info(f"Username field focused: {username_field}")
            
            # Type username
            self.nova_act.page.keyboard.type(self.username)
            logger.info("Username entered")
            
            # Find and focus password field
            password_field = self.nova_act.act("Now find the password input field and click on it to focus it.")
            logger.info(f"Password field focused: {password_field}")
            
            # Type password
            self.nova_act.page.keyboard.type(self.password)
            logger.info("Password entered")
            
            # Submit form
            submit_result = self.nova_act.act("Click the sign in button to submit the login form.")
            logger.info(f"Submit result: {submit_result}")
            
            # Wait and check login success
            self.nova_act.page.wait_for_timeout(3000)
            
            login_check = self.nova_act.act(
                "Check if the login was successful. Look for signs that I'm now logged in, "
                "such as a user menu, account dashboard, or welcome message. "
                "If there are any error messages, please report them."
            )
            logger.info(f"Login check: {login_check}")
            
            return True
            
        except Exception as e:
            logger.error(f"Login attempt failed: {e}")
            return False
    
    def find_informed_delivery(self) -> bool:
        """Navigate to Informed Delivery section."""
        try:
            # Look for Informed Delivery
            self.nova_act.act(
                "Click 'Informed Delivery' option in the "
                "'Receive' dropdown menu in the top navigation bar."
            )
            logger.info(f"Informed Delivery search")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to find Informed Delivery: {e}")
            return False
    
    def check_mail_images(self) -> List[str]:
        """Check for today's mail images and upload to S3."""
        uploaded_files = []
        
        try:
            # Check what's available
            mail_check = self.nova_act.act(
                "I am now in my Informed Delivery section. Look for today's mail images "
            )
            logger.info(f"Mail check: {mail_check}")
            
            # Search for mail images
            selectors = [
                'img[alt*="Mail Piece Images"]',
                'img[alt*="mail"]',
                'img[src*="mail"]'
            ]
            
            all_images = []
            for selector in selectors:
                images = self.nova_act.page.query_selector_all(selector)
                all_images.extend(images)
                if images:
                    logger.info(f"Found {len(images)} images with selector: {selector}")
            
            # Remove duplicates
            unique_images = []
            seen_srcs = set()
            for img in all_images:
                src = img.get_attribute('src')
                if src and src not in seen_srcs:
                    unique_images.append(img)
                    seen_srcs.add(src)
            
            logger.info(f"Found {len(unique_images)} unique mail images")
            
            # Process each image
            for i, img in enumerate(unique_images):
                try:
                    src = img.get_attribute('src')
                    if src:
                        logger.info(f"Processing image {i+1}: {src}")
                        
                        # Take screenshot of the image element
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"mail_image_{i+1}_{timestamp}.png"
                        
                        # Screenshot to bytes
                        screenshot_bytes = img.screenshot()
                        
                        # Upload to S3
                        if self._upload_to_s3(screenshot_bytes, filename):
                            uploaded_files.append(f"s3://{self.s3_bucket}/{self.today}/{filename}")
                        
                except Exception as e:
                    logger.warning(f"Failed to process image {i+1}: {e}")
                    continue
            
            # Fallback: full page screenshot if no images found
            if not uploaded_files:
                logger.info("No images found, taking full page screenshot")
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"mail_preview_full_{timestamp}.png"
                    
                    screenshot_bytes = self.nova_act.page.screenshot(full_page=True)
                    
                    if self._upload_to_s3(screenshot_bytes, filename):
                        uploaded_files.append(f"s3://{self.s3_bucket}/{self.today}/{filename}")
                        
                except Exception as e:
                    logger.error(f"Full page screenshot failed: {e}")
            
        except Exception as e:
            logger.error(f"Failed to check mail images: {e}")
        
        return uploaded_files
    
    def run(self) -> Dict[str, Any]:
        """Run the automation and return results."""
        start_time = datetime.now()
        uploaded_files = []
        success = False
        error_message = None
        method = "nova_act"
        
        try:
            logger.info("Starting USPS Lambda automation with Nova Act...")
            
            self.initialize_nova_act()
            self.start_and_navigate()
            
            if self.attempt_login():
                logger.info("Login successful, proceeding...")
                
                if self.find_informed_delivery():
                    logger.info("Found Informed Delivery, checking for mail...")
                    uploaded_files = self.check_mail_images()
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
            if self.nova_act:
                try:
                    self.nova_act.stop()
                except:
                    pass
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "success": success,
            "images_downloaded": len(uploaded_files),
            "s3_uploads": len(uploaded_files),
            "uploaded_files": uploaded_files,
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
    aws_region = os.environ.get('AWS_REGION', 'us-east-1')  # AWS_REGION is automatically provided by Lambda
    
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