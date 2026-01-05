"""
USPS authentication and navigation module.
Handles login and navigation to Informed Delivery.
"""

import logging
from typing import Optional
from nova_act import NovaAct

logger = logging.getLogger(__name__)


class USPSAuthenticator:
    """Handles USPS website authentication and navigation."""
    
    def __init__(self, nova_act: NovaAct, username: str, password: str):
        self.nova_act = nova_act
        self.username = username
        self.password = password
    
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
            
            # Check login success
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