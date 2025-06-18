import requests
import uuid
import datetime
import time
import imaplib
import email
import re
from playwright.async_api import async_playwright
import asyncio
from nextcaptcha import NextCaptchaAPI # <-- Import the new library
import random

# --- CONFIGURATION ---
GRAPHQL_URL = "https://www.instacart.com/graphql"
NEXTCAPTCHA_API_KEY = "next_8ddbd1b4d50d86c2059e4ff6a96761d28a" # <-- Add your API key

# --- UPDATE THESE HASHES FROM YOUR OWN NETWORK LOG ---
GET_EMAIL_AVAILABILITY_HASH = "PASTE_HASH_FOR_getEmailAvailability_HERE"
SEND_VERIFICATION_CODE_HASH = "PASTE_HASH_FOR_sendVerificationCode_HERE"
CREATE_USER_FROM_CODE_HASH = "PASTE_HASH_FOR_createUserFromVerificationCode_HERE"

class InstacartGenerator:
    def __init__(self, proxy):
        self.session = requests.Session()
        self.playwright_proxy = None
        if proxy:
            try:
                parts = proxy.split(':')
                host, port, user, password = parts[0], parts[1], parts[2], parts[3]
                proxy_url = f"http://{user}:{password}@{host}:{port}"
                self.session.proxies = {'http': proxy_url, 'https': proxy_url}
                self.playwright_proxy = { "server": f"http://{host}:{port}", "username": user, "password": password }
                print(f"Successfully configured proxy: {host}:{port}")
            except Exception as e:
                print(f"Error parsing proxy: {e}. Proceeding without proxy.")

        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'})
        self.auth_config_token = None
        self.forter_token = None
        self.captcha_client = NextCaptchaAPI(client_key=NEXTCAPTCHA_API_KEY)

    async def _initialize_session_and_interact(self, email_address):
        """Final version: Mimics human behavior to avoid detection."""
        print("Initializing human mimicry mode...")
        browser = None
        try:
            async with async_playwright() as p:
                # We need to see what the bot is doing. Headless is for production.
                browser = await p.chromium.launch(headless=False, proxy=self.playwright_proxy)
                context = await browser.new_context(
                    user_agent=self.session.headers['User-Agent'],
                    # Mimic a real screen size
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()

                # ... (handle_response function remains the same) ...
                auth_token_found = asyncio.Event()
                def handle_response(response):
                    if "graphql" in response.url and response.request.method == "POST":
                        try:
                            json_data = asyncio.run(response.json())
                            if json_data.get("data", {}).get("authConfiguration", {}).get("authConfigurationToken"):
                                self.auth_config_token = json_data["data"]["authConfiguration"]["authConfigurationToken"]
                                print(f"[DEBUG] Captured Auth Config Token.")
                                auth_token_found.set()
                        except: pass
                page.on("response", handle_response)

                await page.goto("https://www.instacart.com/signup", timeout=60000)
                print("Page loaded. Simulating human interaction...")

                email_input_selector = 'input[name="email"]'
                await page.wait_for_selector(email_input_selector, timeout=15000)

                # --- HUMAN MIMICRY ---
                # 1. Move the mouse over the input field like a person would
                await page.hover(email_input_selector)
                await asyncio.sleep(random.uniform(0.3, 0.7)) # Think for a moment

                # 2. Type like a human, with small delays between keystrokes
                await page.type(email_input_selector, email_address, delay=random.randint(50, 150))
                await asyncio.sleep(random.uniform(0.5, 1.0)) # Admire your typing

                continue_button_selector = 'button[type="submit"]'
                await page.hover(continue_button_selector)
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await page.click(continue_button_selector)
                print("Interaction complete. Waiting for CAPTCHA or response...")
                
                # --- FINAL CAPTCHA LOGIC ---
                try:
                    await page.wait_for_timeout(3000) # Wait for the iframe to be injected
                    iframe_selector = 'iframe[src*="google.com/recaptcha"]'
                    iframe_element = await page.query_selector(iframe_selector)
                    
                    if not iframe_element:
                        # --- BETTER DEBUGGING: Save evidence of failure ---
                        print("[FAILURE] CAPTCHA iframe not found. The anti-bot likely blocked us.")
                        await page.screenshot(path='failure_screenshot.png')
                        with open('failure_page_source.html', 'w', encoding='utf-8') as f:
                            f.write(await page.content())
                        print("Saved screenshot and page source for analysis.")
                        raise Exception("CAPTCHA iframe was not found in the DOM.")

                    # ... (The rest of the CAPTCHA solving logic from the previous step) ...
                    
                except Exception as e:
                    raise e # Re-raise the exception to be caught by the outer block

                # ... (The rest of the token grabbing logic) ...
                
                await browser.close()
                return True
        except Exception as e:
            print(f"[CRITICAL ERROR] The final attempt failed.")
            import traceback
            traceback.print_exc()
            if browser:
                await browser.close()
            return False

    async def _send_verification_code(self, email_address):
        """Sends the verification code using the captured tokens."""
        print(f"Requesting verification code for {email_address}...")
        payload = { "operationName": "sendVerificationCode", "variables": { "email": email_address, "token": self.auth_config_token, "forterToken": self.forter_token }, "extensions": { "persistedQuery": { "version": 1, "sha256Hash": SEND_VERIFICATION_CODE_HASH } } }
        try:
            r = self.session.post(GRAPHQL_URL, json=payload)
            r.raise_for_status()
            return "errors" not in r.json()
        except Exception as e:
            print(f"Error sending verification code: {e}")
            return False

    async def _get_code_from_email(self, imap_details):
        """Connects to IMAP server and retrieves the 6-digit verification code."""
        print("Connecting to IMAP server to find verification code...")
        for i in range(4): # Try for 60 seconds (4 * 15s)
            try:
                mail = imaplib.IMAP4_SSL(imap_details['server'])
                mail.login(imap_details['user'], imap_details['pass'])
                mail.select('inbox')
                
                status, data = mail.search(None, '(UNSEEN FROM "instacart.com")')
                mail_ids = data[0].split()

                if mail_ids:
                    latest_id = mail_ids[-1]
                    status, data = mail.fetch(latest_id, '(RFC822)')
                    msg = email.message_from_bytes(data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                    
                    code_match = re.search(r'(\d{6})', body)
                    if code_match:
                        code = code_match.group(1)
                        print(f"Found code: {code}")
                        mail.logout()
                        return code
                mail.logout()
            except Exception as e:
                print(f"IMAP Error: {e}")

            print(f"Code not found, waiting 15 seconds... (Attempt {i+1}/4)")
            await asyncio.sleep(15)
        return None

    async def _create_user_from_verification_code(self, email_address, password, verification_code):
        """Finalizes account creation with the code."""
        print(f"Finalizing account with code {verification_code}...")
        payload = { "operationName": "createUserFromVerificationCode", "variables": { "email": email_address, "password": password, "code": verification_code }, "extensions": { "persistedQuery": { "version": 1, "sha256Hash": CREATE_USER_FROM_CODE_HASH } } }
        try:
            r = self.session.post(GRAPHQL_URL, json=payload)
            data = r.json()
            if "errors" in data:
                return f"FAILED: {data['errors'][0]['message']}"
            else:
                auth_token = data.get("data", {}).get("createUserFromVerificationCode", {}).get("authToken", {}).get("token")
                return f"SUCCESS: {email_address}:{password} | Token: {auth_token[:20]}..."
        except Exception as e:
            print(f"Error finalizing account: {e}")
            return f"FAILED: Critical error during finalization."

    async def run(self, email_address, password, imap_details):
        """Executes the full generation sequence."""
        if not await self._initialize_session_and_interact(email_address):
             return "Failed: Browser initialization and interaction failed."

        # The _check_email_availability step is often implicitly handled by the signup form's interaction.
        # If it fails at the next step, it's because the email was unavailable.
        # We can therefore skip the separate check for a more efficient flow.
        
        if not await self._send_verification_code(email_address):
            return "Failed: Could not send verification code. The email may be taken or the session was flagged."
        
        code = await self._get_code_from_email(imap_details)
        if not code: 
            return "Failed: Could not retrieve verification code from email."
        
        result = await self._create_user_from_verification_code(email_address, password, code)
        return result