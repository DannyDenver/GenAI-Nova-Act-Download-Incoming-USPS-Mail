"""
Nova Act configuration and initialization module.
Handles Nova Act setup for Lambda environment.
"""

import os
import glob
import logging
from typing import Optional
from nova_act import NovaAct

logger = logging.getLogger(__name__)


class NovaActConfig:
    """Handles Nova Act configuration and initialization."""
    
    def __init__(self, logs_dir: str):
        self.logs_dir = logs_dir
        self.nova_act: Optional[NovaAct] = None
    
    def initialize(self) -> NovaAct:
        """Initialize Nova Act for Lambda environment."""
        try:
            # Create logs directory
            os.makedirs(self.logs_dir, exist_ok=True)
            
            # Set environment variables for Microsoft Playwright image
            self._setup_playwright_environment()
            
            # Log environment info for debugging
            self._log_environment_info()
            
            # Check for Chromium executable
            self._check_chromium_executable()
            
            logger.info("Attempting Nova Act initialization with Microsoft Playwright image...")
            
            # Initialize Nova Act with configuration
            self.nova_act = NovaAct(
                starting_page="https://www.usps.com/",
                headless=True,  # Always headless in Lambda
                logs_directory=self.logs_dir,
                clone_user_data_dir=False,  # Don't clone user data in Lambda
                go_to_url_timeout=60,
                nova_act_api_key=os.environ.get("NOVA_ACT_API_KEY"),
                chrome_channel="chromium"
            )
            
            logger.info("Nova Act initialized successfully for Lambda")
            return self.nova_act
                
        except Exception as e:
            logger.error(f"Failed to initialize Nova Act: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _setup_playwright_environment(self) -> None:
        """Set up Playwright environment variables."""
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/ms-playwright'
        os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'
        os.environ['NOVA_ACT_SKIP_PLAYWRIGHT_INSTALL'] = '1'
    
    def _log_environment_info(self) -> None:
        """Log environment information for debugging."""
        logger.info(f"Python version: {os.sys.version}")
        logger.info(f"PLAYWRIGHT_BROWSERS_PATH: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
        
        playwright_dir = '/ms-playwright'
        if os.path.exists(playwright_dir):
            logger.info(f"Available files in /ms-playwright: {os.listdir(playwright_dir)}")
        else:
            logger.info("Directory /ms-playwright not found")
    
    def _check_chromium_executable(self) -> None:
        """Check for Chromium executable availability."""
        chromium_paths = [
            '/ms-playwright/chromium-*/chrome-linux/chrome',
            '/ms-playwright/chromium-*/chrome-linux/headless_shell',
            '/ms-playwright/chromium*/chrome-linux/chrome',
            '/ms-playwright/chromium*/chrome-linux/headless_shell'
        ]
        
        for pattern in chromium_paths:
            matches = glob.glob(pattern)
            if matches:
                logger.info(f"Found Chromium executable(s): {matches}")
                return
        
        logger.warning("No Chromium executable found in expected locations")
    
    def stop(self) -> None:
        """Stop Nova Act session safely."""
        if self.nova_act:
            try:
                self.nova_act.stop()
                logger.info("Nova Act session stopped")
            except Exception as e:
                logger.warning(f"Error stopping Nova Act: {e}")