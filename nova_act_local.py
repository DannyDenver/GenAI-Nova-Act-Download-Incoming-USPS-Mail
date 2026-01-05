#!/usr/bin/env python3
"""
Local USPS Informed Delivery automation using Nova Act.
Runs locally without AWS dependencies.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from nova_act import NovaAct
from nova_act.types.act_result import ActResult
from nova_act.types.act_errors import ActAgentError, ActClientError, ActExecutionError, ActServerError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LocalUSPSAutomator:
    """Local USPS automation class without AWS dependencies."""
    
    def __init__(self, username: str, password: str, output_dir: str = "mail_images"):
        self.username = username
        self.password = password
        self.output_dir = output_dir
        self.nova_act: Optional[NovaAct] = None
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create date-based folder structure
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.today_dir = os.path.join(self.output_dir, self.today)
        os.makedirs(self.today_dir, exist_ok=True)
    
    def _save_to_file(self, file_data: bytes, filename: str) -> bool:
        """Save file data to local directory."""
        file_path = os.path.join(self.today_dir, filename)
        
        try:
            with open(file_path, 'wb') as f:
                f.write(file_data)
            logger.info(f"✓ Saved to file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save {filename}: {e}")
            return False
    
    def _save_logs_to_file(self) -> List[str]:
        """Save Nova Act logs to local directory."""
        saved_logs = []
        
        if not hasattr(self, 'logs_dir') or not os.path.exists(self.logs_dir):
            logger.warning("No logs directory found to save")
            return saved_logs
        
        # Create logs subdirectory
        logs_output_dir = os.path.join(self.today_dir, "logs")
        os.makedirs(logs_output_dir, exist_ok=True)
        
        try:
            # Walk through logs directory and copy all files
            for root, dirs, files in os.walk(self.logs_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Skip empty files
                    if os.path.getsize(file_path) == 0:
                        logger.debug(f"Skipping empty file: {file_path}")
                        continue
                    
                    # Create relative path for output
                    rel_path = os.path.relpath(file_path, self.logs_dir)
                    output_path = os.path.join(logs_output_dir, rel_path)
                    
                    # Create subdirectories if needed
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    try:
                        # Copy file
                        with open(file_path, 'rb') as src, open(output_path, 'wb') as dst:
                            dst.write(src.read())
                        
                        saved_logs.append(output_path)
                        logger.info(f"✓ Saved log to: {output_path}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to save log file {file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to save logs: {e}")
        
        logger.info(f"Saved {len(saved_logs)} log files")
        return saved_logs
    
    def initialize_nova_act(self) -> None:
        """Initialize Nova Act for local environment."""
        try:
            # Create logs directory in current working directory
            self.logs_dir = os.path.join(self.output_dir, "nova_act_logs")
            os.makedirs(self.logs_dir, exist_ok=True)
            
            logger.info("Initializing Nova Act for local environment...")
            
            # Initialize Nova Act with local configuration
            self.nova_act = NovaAct(
                starting_page="https://www.usps.com/",
                headless=False,  # Can be visible for local testing
                logs_directory=self.logs_dir,
                clone_user_data_dir=False,
                go_to_url_timeout=60,
                nova_act_api_key=os.environ.get("NOVA_ACT_API_KEY")
            )
            
            logger.info("Nova Act initialized successfully for local environment")
                
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
            
            # Navigate to sign in with explicit URL tracking to prevent loops
            current_url = self.nova_act.page.url
            logger.info(f"Starting URL: {current_url}")
            
            account_search = self.nova_act.act(
                "I need to access my personal USPS account to check my mail. "
                "Click on the 'sign in' button on the top right of the main page. "
                "If you're already on a sign-in page, just proceed to the login form."
            )
            logger.info(f"Navigation result: {account_search}")
            
        except Exception as e:
            logger.error(f"Failed to start and navigate: {e}")
            raise
    
    def attempt_login(self) -> bool:
        """Attempt to login with credentials."""
        try:
            # self.nova_act.page.wait_for_timeout(3000)
            
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
            # self.nova_act.page.wait_for_timeout(6000)
            
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
            # Track current URL to detect navigation loops
            current_url = self.nova_act.page.url
            logger.info(f"Current URL before Informed Delivery search: {current_url}")
            
            # Look for Informed Delivery with loop prevention
            delivery_result = self.nova_act.act(
                "Click 'Informed Delivery' button or link. "
                "If you're already on the Informed Delivery page, just proceed."
            )
            logger.info(f"Informed Delivery navigation: {delivery_result}")
            
            # Look for sign-in button with specific context
            signin_result = self.nova_act.act(
                "Look for and click a 'Sign In' button specifically for Informed Delivery. "
                "It might be below title text that says 'Informed Delivery by USPS'. "
                "If you're already signed in or on the main Informed Delivery page, just proceed."
            )
            logger.info(f"Informed Delivery sign-in: {signin_result}")

            return True
            
        except Exception as e:
            logger.error(f"Failed to find Informed Delivery: {e}")
            return False
    
    def check_mail_images(self) -> List[str]:
        """Check for today's mail images and save to local directory."""
        saved_files = []
        
        # Check if address filtering is enabled
        
        try:
            # Check what's available
            mail_check = self.nova_act.act(
                "I am now in my Informed Delivery section. Look for today's mail images "
            )
            logger.info(f"Mail check: {mail_check}")
            
            # Search for mail images and filter for those with addresses
            selectors = [
                'img[alt*="Mail Piece Images"]',
                'img[alt*="mail"]',
                'img[src*="mail"]'
            ]
            
            all_images = []
            for selector in selectors:
                images = self.nova_act.page.query_selector_all(selector)
                logger.info(f"Found {len(images)} potential images with selector: {selector}")
                
                # Check each image for address content using Nova Act
                for i, img in enumerate(images):
                    try:
                        # First, check if the image source or alt text suggests it's a mail piece
                        src = img.get_attribute('src') or ''
                        alt = img.get_attribute('alt') or ''
                        
                        # Skip obvious non-mail images
                        skip_keywords = ['logo', 'banner', 'icon', 'button', 'nav']
                        if any(keyword in src.lower() or keyword in alt.lower() for keyword in skip_keywords):
                            logger.info(f"✗ Skipping image {i+1} - appears to be UI element: {src}")
                            continue
                        
                        # Use Nova Act to analyze the image content for address information
                        analysis_result = self.nova_act.act(
                            f"Examine this mail image carefully. Look for addressing information such as: "
                            f"- Recipient name and address "
                            f"- Street address, city, state, zip code "
                            f"- Return address information "
                            f"- Any text that looks like mailing labels "
                            f"Respond with 'HAS_ADDRESS' if you can clearly see addressing information, "
                            f"or 'NO_ADDRESS' if it's blank, just a logo, or contains no addressing text.",
                            element=img
                        )
                        
                        # Check if Nova Act found address information
                        analysis_text = str(analysis_result).upper()
                        if 'HAS_ADDRESS' in analysis_text or any(keyword in analysis_text for keyword in ['ADDRESS', 'RECIPIENT', 'STREET', 'ZIP']):
                            all_images.append(img)
                            logger.info(f"✓ Image {i+1} contains address information: {analysis_result}")
                        else:
                            logger.info(f"✗ Image {i+1} filtered out - no address information: {analysis_result}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to analyze image {i+1}: {e}")
                        # If analysis fails, include the image to be safe (better to have false positives)
                        all_images.append(img)
                        logger.info(f"⚠ Including image {i+1} due to analysis failure")
                        continue
            
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
                        
                        # Save to local file
                        if self._save_to_file(screenshot_bytes, filename):
                            saved_files.append(os.path.join(self.today_dir, filename))
                        
                except Exception as e:
                    logger.warning(f"Failed to process image {i+1}: {e}")
                    continue
            
            # Fallback: full page screenshot if no images found
            if not saved_files:
                logger.info("No images found, taking full page screenshot")
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"mail_preview_full_{timestamp}.png"
                    
                    screenshot_bytes = self.nova_act.page.screenshot(full_page=True)
                    
                    if self._save_to_file(screenshot_bytes, filename):
                        saved_files.append(os.path.join(self.today_dir, filename))
                        
                except Exception as e:
                    logger.error(f"Full page screenshot failed: {e}")
            
        except Exception as e:
            logger.error(f"Failed to check mail images: {e}")
        
        return saved_files
    
    def run(self) -> Dict[str, Any]:
        """Run the automation and return results."""
        start_time = datetime.now()
        saved_files = []        
        saved_logs = []
        success = False
        error_message = None
        method = "nova_act_local"
        
        try:
            logger.info("Starting local USPS automation with Nova Act...")
            
            self.initialize_nova_act()
            self.start_and_navigate()
            
            if self.attempt_login():
                logger.info("Login successful, proceeding...")
                
                if self.find_informed_delivery():
                    logger.info("Found Informed Delivery, checking for mail...")
                    saved_files = self.check_mail_images()
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
            if self.nova_act:
                try:
                    self.nova_act.stop()
                    logger.info("Nova Act session stopped")
                except Exception as e:
                    logger.warning(f"Error stopping Nova Act: {e}")
            
            # Save logs to local directory (if enabled)
            save_logs = os.environ.get('SAVE_LOGS', 'true').lower() == 'true'
            if save_logs:
                try:
                    logger.info("Saving Nova Act logs to local directory...")
                    saved_logs = self._save_logs_to_file()
                except Exception as e:
                    logger.error(f"Failed to save logs: {e}")
            else:
                logger.info("Log saving disabled via SAVE_LOGS environment variable")
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "success": success,
            "images_downloaded": len(saved_files),
            "files_saved": len(saved_files),
            "saved_files": saved_files,
            "saved_logs": saved_logs,
            "logs_saved": len(saved_logs),
            "execution_time": execution_time,
            "date": self.today,
            "method": method,
            "error_message": error_message,
            "output_directory": self.today_dir
        }


def main():
    """Main function for local execution."""
    # Get credentials from environment variables
    username = os.environ.get('USPS_USERNAME')
    password = os.environ.get('USPS_PASSWORD')
    nova_act_api_key = os.environ.get('NOVA_ACT_API_KEY')
    
    if not username or not password:
        logger.error("Missing required environment variables: USPS_USERNAME, USPS_PASSWORD")
        logger.error("Please set these environment variables before running:")
        logger.error("export USPS_USERNAME='your-username'")
        logger.error("export USPS_PASSWORD='your-password'")
        logger.error("export NOVA_ACT_API_KEY='your-api-key'")
        logger.error("")
        logger.error("Optional environment variables:")
        logger.error("export OUTPUT_DIR='mail_images'  # Default output directory")
        logger.error("export SAVE_LOGS='true'  # Save Nova Act logs")
        logger.error("export FILTER_ADDRESS_IMAGES='true'  # Filter images with addresses only")
        return
    
    if not nova_act_api_key:
        logger.error("Missing NOVA_ACT_API_KEY environment variable")
        logger.error("Please set: export NOVA_ACT_API_KEY='your-api-key'")
        return
    
    # Create output directory
    output_dir = os.environ.get('OUTPUT_DIR', 'mail_images')
    
    try:
        # Create and run automator
        automator = LocalUSPSAutomator(username, password, output_dir)
        result = automator.run()
        
        # Print results
        logger.info("=" * 50)
        logger.info("AUTOMATION COMPLETED")
        logger.info("=" * 50)
        logger.info(f"Success: {result['success']}")
        logger.info(f"Images downloaded: {result['images_downloaded']}")
        logger.info(f"Files saved: {result['files_saved']}")
        logger.info(f"Logs saved: {result['logs_saved']}")
        logger.info(f"Execution time: {result['execution_time']:.2f} seconds")
        logger.info(f"Output directory: {result['output_directory']}")
        
        if result['saved_files']:
            logger.info("Saved files:")
            for file_path in result['saved_files']:
                logger.info(f"  - {file_path}")
        
        if result['error_message']:
            logger.error(f"Error: {result['error_message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Local execution failed: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    main()