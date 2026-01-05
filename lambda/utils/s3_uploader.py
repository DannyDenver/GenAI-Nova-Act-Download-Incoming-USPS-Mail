"""
S3 upload and log management module.
Handles file uploads to S3 and log processing.
"""

import os
import logging
from datetime import datetime
from typing import List
import boto3

logger = logging.getLogger(__name__)


class S3Uploader:
    """Handles S3 uploads for images and logs."""
    
    def __init__(self, s3_bucket: str, aws_region: str):
        self.s3_bucket = s3_bucket
        self.aws_region = aws_region
        self.s3_client = boto3.client('s3', region_name=aws_region)
        self.today = datetime.now().strftime("%Y-%m-%d")
    
    def upload_file(self, file_data: bytes, filename: str, content_type: str = 'image/png') -> bool:
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
    
    def upload_logs(self, logs_dir: str) -> List[str]:
        """Upload Nova Act logs to S3."""
        uploaded_logs = []
        
        if not os.path.exists(logs_dir):
            logger.warning("No logs directory found to upload")
            return uploaded_logs
        
        try:
            # Walk through logs directory and upload all files
            for root, dirs, files in os.walk(logs_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Skip empty files
                    if os.path.getsize(file_path) == 0:
                        logger.debug(f"Skipping empty file: {file_path}")
                        continue
                    
                    # Create relative path for S3 key
                    rel_path = os.path.relpath(file_path, logs_dir)
                    s3_key = f"{self.today}/logs/{rel_path}"
                    
                    try:
                        # Determine content type based on file extension
                        content_type = self._get_content_type(file)
                        
                        # Read and upload file
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                        
                        self.s3_client.put_object(
                            Bucket=self.s3_bucket,
                            Key=s3_key,
                            Body=file_data,
                            ContentType=content_type,
                            Metadata={
                                'upload-date': self.today,
                                'source': 'nova-act-logs',
                                'automation-version': '1.0',
                                'log-type': 'automation-trace',
                                'file-size': str(len(file_data))
                            }
                        )
                        
                        uploaded_logs.append(f"s3://{self.s3_bucket}/{s3_key}")
                        logger.info(f"✓ Uploaded log to S3: {s3_key} ({len(file_data)} bytes)")
                        
                    except Exception as e:
                        logger.warning(f"Failed to upload log file {file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to upload logs to S3: {e}")
        
        logger.info(f"Uploaded {len(uploaded_logs)} log files to S3")
        return uploaded_logs
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type based on file extension."""
        if filename.endswith('.json'):
            return 'application/json'
        elif filename.endswith('.html'):
            return 'text/html'
        elif filename.endswith('.png'):
            return 'image/png'
        elif filename.endswith('.log'):
            return 'text/plain'
        else:
            return 'text/plain'