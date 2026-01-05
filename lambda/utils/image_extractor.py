"""
Image extraction and processing module.
Handles finding, analyzing, and capturing mail images.
"""

import logging
from datetime import datetime
from typing import List, Callable
from nova_act import NovaAct

logger = logging.getLogger(__name__)


class MailImageExtractor:
    """Handles extraction and processing of mail images."""
    
    def __init__(self, nova_act: NovaAct, upload_callback: Callable[[bytes, str], bool]):
        self.nova_act = nova_act
        self.upload_callback = upload_callback
        self.today = datetime.now().strftime("%Y-%m-%d")
    
    def check_mail_images(self) -> List[str]:
        """Check for today's mail images and process them."""
        uploaded_files = []
        
        try:
            # Check what's available
            mail_check = self.nova_act.act(
                "I am now in my Informed Delivery section. Look for today's mail images "
            )
            logger.info(f"Mail check: {mail_check}")
            
            # Find and analyze images
            all_images = self._find_and_analyze_images()
            
            # Remove duplicates
            unique_images = self._remove_duplicate_images(all_images)
            logger.info(f"Found {len(unique_images)} unique mail images")
            
            # Process each image
            for i, img in enumerate(unique_images):
                try:
                    uploaded_file = self._process_single_image(img, i + 1)
                    if uploaded_file:
                        uploaded_files.append(uploaded_file)
                        
                except Exception as e:
                    logger.warning(f"Failed to process image {i+1}: {e}")
                    continue
            
            # Fallback: full page screenshot if no images found
            if not uploaded_files:
                fallback_file = self._take_fallback_screenshot()
                if fallback_file:
                    uploaded_files.append(fallback_file)
            
        except Exception as e:
            logger.error(f"Failed to check mail images: {e}")
        
        return uploaded_files
    
    def _find_and_analyze_images(self) -> List:
        """Find and analyze images for address content."""
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
                    if self._should_include_image(img, i + 1):
                        all_images.append(img)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze image {i+1}: {e}")
                    # If analysis fails, include the image to be safe
                    all_images.append(img)
                    logger.info(f"⚠ Including image {i+1} due to analysis failure")
                    continue
        
        return all_images
    
    def _should_include_image(self, img, image_num: int) -> bool:
        """Determine if an image should be included based on content analysis."""
        # First, check if the image source or alt text suggests it's a mail piece
        src = img.get_attribute('src') or ''
        alt = img.get_attribute('alt') or ''
        
        # Skip obvious non-mail images
        skip_keywords = ['logo', 'banner', 'icon', 'button', 'nav']
        if any(keyword in src.lower() or keyword in alt.lower() for keyword in skip_keywords):
            logger.info(f"✗ Skipping image {image_num} - appears to be UI element: {src}")
            return False
        
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
        has_address = ('HAS_ADDRESS' in analysis_text or 
                      any(keyword in analysis_text for keyword in ['ADDRESS', 'RECIPIENT', 'STREET', 'ZIP']))
        
        if has_address:
            logger.info(f"✓ Image {image_num} contains address information: {analysis_result}")
            return True
        else:
            logger.info(f"✗ Image {image_num} filtered out - no address information: {analysis_result}")
            return False
    
    def _remove_duplicate_images(self, all_images: List) -> List:
        """Remove duplicate images based on src attribute."""
        unique_images = []
        seen_srcs = set()
        
        for img in all_images:
            src = img.get_attribute('src')
            if src and src not in seen_srcs:
                unique_images.append(img)
                seen_srcs.add(src)
        
        return unique_images
    
    def _process_single_image(self, img, image_num: int) -> str:
        """Process a single image and return the uploaded file path."""
        src = img.get_attribute('src')
        if not src:
            return None
            
        logger.info(f"Processing image {image_num}: {src}")
        
        # Wait for image to be fully loaded
        self._wait_for_image_load(img, image_num)
        
        # Take screenshot with retry logic
        screenshot_bytes = self._take_image_screenshot(img, image_num)
        
        if screenshot_bytes:
            # Generate filename and upload
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"mail_image_{image_num}_{timestamp}.png"
            
            if self.upload_callback(screenshot_bytes, filename):
                return f"s3://bucket/{self.today}/{filename}"  # Will be updated by caller
        else:
            logger.warning(f"No screenshot data for image {image_num}")
            
        return None
    
    def _wait_for_image_load(self, img, image_num: int) -> None:
        """Wait for image to be fully loaded before screenshot."""
        try:
            # Wait for the image element to be stable
            self.nova_act.page.wait_for_timeout(2000)
            
            # Check if image is loaded
            is_loaded = img.evaluate("img => img.complete && img.naturalHeight !== 0")
            if not is_loaded:
                logger.warning(f"Image {image_num} may not be fully loaded, waiting...")
                self.nova_act.page.wait_for_timeout(3000)
        except Exception as load_check_error:
            logger.warning(f"Could not verify image load status: {load_check_error}")
    
    def _take_image_screenshot(self, img, image_num: int) -> bytes:
        """Take screenshot of image with retry logic."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Increase timeout to 60 seconds and add retry logic
                return img.screenshot(timeout=60000)
            except Exception as screenshot_error:
                logger.warning(f"Screenshot attempt {attempt + 1} failed for image {image_num}: {screenshot_error}")
                if attempt < max_retries - 1:
                    # Wait a bit before retrying
                    self.nova_act.page.wait_for_timeout(2000)
                else:
                    logger.error(f"All screenshot attempts failed for image {image_num}")
                    raise screenshot_error
        
        return None
    
    def _take_fallback_screenshot(self) -> str:
        """Take full page screenshot as fallback."""
        logger.info("No images found, taking full page screenshot")
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"mail_preview_full_{timestamp}.png"
            
            # Full page screenshot with increased timeout and retry logic
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    screenshot_bytes = self.nova_act.page.screenshot(full_page=True, timeout=90000)
                    
                    if self.upload_callback(screenshot_bytes, filename):
                        return f"s3://bucket/{self.today}/{filename}"  # Will be updated by caller
                    break
                except Exception as screenshot_error:
                    logger.warning(f"Full page screenshot attempt {attempt + 1} failed: {screenshot_error}")
                    if attempt < max_retries - 1:
                        self.nova_act.page.wait_for_timeout(3000)
                    else:
                        logger.error("All full page screenshot attempts failed")
                        raise screenshot_error
                        
        except Exception as e:
            logger.error(f"Full page screenshot failed: {e}")
        
        return None