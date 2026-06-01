import os
import pickle
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

class FacebookBot:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None
        # Save to /app/downloads to leverage the Docker Compose Volume
        self.cookie_file = "/app/downloads/fb_cookies.pkl" 
        self.remote_url = os.getenv("SELENIUM_REMOTE_URL", "http://localhost:4444/wd/hub")

    def init_driver(self, headless=True):
        """Initializes a new driver session dynamically."""
        # Clean up any existing active driver session first
        self.close_driver()

        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.page_load_strategy = "eager"

        # Image blocking to optimize speed (Disable it if it disrupts your login process)

        # Note: Headless mode is omitted here because the 'selenium/standalone-chrome' 
        # container manages its own virtual desktop (Xvfb) automatically.

        print(f"🌐 Creating a new Browser session (Connection: {self.remote_url})...")
        self.driver = webdriver.Remote(command_executor=self.remote_url, options=options)

    def close_driver(self):
        """Safely shuts down the browser instance to free up RAM."""
        if self.driver:
            try:
                self.driver.quit()
                print("🔒 Browser window closed successfully.")
            except Exception as e:
                print(f"⚠️ Error closing driver: {e}")
            finally:
                self.driver = None

    def save_cookies(self):
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            with open(self.cookie_file, "wb") as f:
                pickle.dump(self.driver.get_cookies(), f)
            print("🍪 Cookies updated & saved to Host machine.")
            return True
        except Exception as e:
            print(f"❌ Save cookies failed: {e}")
            return False

    def is_logged_in(self, timeout=5):
        if not self.driver:
            return False
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: (
                    d.find_elements(By.NAME, "email") or   # Login form
                    d.find_elements(By.XPATH, "//div[@role='navigation']") # Home page UI
                )
            )
            if self.driver.find_elements(By.NAME, "email"):
                return False
            if self.driver.find_elements(By.XPATH, "//div[@role='navigation']"):
                return True
            return False
        except:
            return False

    def handle_checkpoint(self):
        try:
            btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@role='button' and contains(., 'Continue')]"))
            )
            btn.click()
            password_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "pass"))
            )
            password_input.clear()
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)
            return True
        except Exception as e:
            print(f"❌ Checkpoint failed or not detected: {e}")
            return False

    def login_with_cookies(self):
        if not os.path.exists(self.cookie_file):
            print("⚠️ Cookie file not found.")
            return False

        try:
            with open(self.cookie_file, "rb") as f:
                cookies = pickle.load(f)
        except Exception as e:
            print(f"❌ Failed to load cookies: {e}")
            return False

        # Start a fast session just to test the validation background layer
        self.init_driver()
        self.driver.get("https://www.facebook.com/")

        success_count = 0
        for cookie in cookies:
            cookie.pop("sameSite", None)
            try:
                self.driver.add_cookie(cookie)
                success_count += 1
            except:
                pass

        print(f"🍪 Injected {success_count}/{len(cookies)} cookies.")
        self.driver.refresh()

        if self.is_logged_in():
            print("✅ Logged in cleanly via cookies.")
            self.save_cookies()
            return True

        self.handle_checkpoint()

        if self.is_logged_in():
            print("✅ Logged in after resolving checkpoint.")
            self.save_cookies()
            return True

        print("❌ Cookie validation failed. Session expired.")
        self.close_driver() # Close it down immediately since it's invalid
        return False

    def login_and_save_cookies(self, timeout=120):
        # Open a completely fresh interface window for you to connect manually
        self.init_driver()
        self.driver.get("https://www.facebook.com/")

        print("\n" + "="*60)
        print("🔐 MANUAL ACTION REQUIRED!")
        print("👉 Please open your desktop browser and go to: http://localhost:7900")
        print(f"⏳ You have {timeout} seconds to complete the login details + OTP...")
        print("="*60 + "\n")

        start = time.time()
        while time.time() - start < timeout:
            if self.is_logged_in():
                print("✅ Manual login detected!")
                self.save_cookies()
                return True
            time.sleep(3)

        print("❌ Timeout: Manual login execution was not completed.")
        self.close_driver()
        return False

    # -------------------------------------------------------------
    # MAIN EXECUTION SMART WORKFLOW
    # -------------------------------------------------------------
    def ensure_login(self):
        """Executes your exact 3-step lifecycle strategy."""
        # Step 1: Attempt non-interactive login via serialized cookies
        success = self.login_with_cookies()

        # Step 2: Fallback to manual interaction if validation fails
        if not success:
            print("🔐 Falling back to explicit manual interaction...")
            success = self.login_and_save_cookies()

        # Step 3: Proceed to business tasks or shut down
        if success:
            print("🚀 Active authentication session acquired! Executing scraping/automation script...")
            self.execute_business_tasks()
        else:
            print("💥 System halted: Unable to verify an active Facebook account session.")
            
        # Guarantee closure at the absolute end of the worker loop execution block
        self.close_driver()

    def execute_business_tasks(self):
        """Your automation code goes here while the verified browser is active."""
        for uid in uids:
            self.send_message_via_uid(uid, "Hello!")
        time.sleep(5)
        print(f"🎬 Current view state title is: '{self.driver.title}'")
        # Add your scrapers/posting logic loop here...

    def send_message_via_uid(self, uid, content):
        def close_chat():
            try:
                print("[+] Đang đóng chat...")

                close_button = self.driver.find_element(
                    By.XPATH,
                    '//div[@aria-label="Close chat"]'
                )

                close_button.click()

                print("[+] Đã đóng chat")

            except Exception as e:
                print(
                    f"[!] Close chat failed UID={uid}: {e}"
                )

        def find_message_button():
            try:
                message_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        '//div[@aria-label="Message" or @aria-label="Nhắn tin"]'
                    ))
                )

                print("[+] Đã tìm thấy nút Message")

            except TimeoutException as e:
                raise Exception(
                    f"[MESSAGE_BUTTON_TIMEOUT] UID={uid}"
                ) from e
            
            except NoSuchElementException as e:
                raise Exception(
                    f"[MESSAGE_BUTTON_NOT_FOUND] UID={uid}"
                ) from e
            
            return message_button
            
        def find_chatbox():
            try:
                chatbox_xpath = (
                    '//div[contains(@aria-label, "Write to")]'
                )

                chatbox = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, chatbox_xpath)
                    )
                )

                print("[+] Đã tìm thấy chatbox")

            except TimeoutException as e:
                close_chat()
                raise Exception(
                    f"[CHATBOX_TIMEOUT] UID={uid}"
                ) from e
            
            return chatbox

        def clear_chatbox():
            try:
                print("[+] Đang clear chatbox...")

                chatbox.send_keys(Keys.CONTROL, "a")
                chatbox.send_keys(Keys.DELETE)

                print("[+] Đã clear chatbox")

            except Exception as e:
                print(
                    f"[!] Clear chatbox failed UID={uid}: {e}"
                )

        try:
            # =========================
            # OPEN PROFILE
            # =========================
            try:
                print(f"\n[+] Đang mở trang cá nhân UID: {uid}")

                user_url = f"https://www.facebook.com/{uid}"
                self.driver.get(user_url)

            except Exception as e:
                raise Exception(
                    f"[OPEN_PROFILE_FAILED] UID={uid}"
                ) from e

            # =========================
            # FIND MESSAGE BUTTON
            # =========================
            message_button = find_message_button()

            
            # =========================
            # CLICK MESSAGE BUTTON
            # =========================
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    message_button
                )

                message_button.click()

                print("[+] Đã click Message")

            except ElementClickInterceptedException as e:
                raise Exception(
                    f"[MESSAGE_BUTTON_CLICK_BLOCKED] UID={uid}"
                ) from e

            except Exception as e:
                raise Exception(
                    f"[MESSAGE_BUTTON_CLICK_FAILED] UID={uid}"
                ) from e

            # =========================
            # FIND CHATBOX
            # =========================
            chatbox = find_chatbox()

            # =========================
            # INPUT MESSAGE
            # =========================
            try:
                print(f"[+] Đang nhập tin nhắn: '{content}'")

                time.sleep(random.uniform(0.2, 0.5))
                chatbox.send_keys(content)

                print("[+] Đã nhập tin nhắn")

            except Exception as e:
                raise Exception(
                    f"[INPUT_MESSAGE_FAILED] UID={uid}"
                ) from e


            # =========================
            # SEND MESSAGE
            # =========================
            try:
                print("[+] Đang gửi tin nhắn...")

                # send_button.click()
                #chatbox.click(Keys.ENTER)
                time.sleep(random.uniform(0.5, 1.5))

                print("[🔑] Gửi thành công!")

            except Exception as e:
                raise Exception(
                    f"[SEND_MESSAGE_FAILED] UID={uid}"
                ) from e


            clear_chatbox()

            close_chat()

            return True

        except Exception as e:
            print(f"[❌] {e}")
            return False

def capture_screenshot(driver: webdriver.Chrome, url: str, download_dir: str) -> str:
    """Truy cập vào URL và tiến hành chụp ảnh màn hình, lưu vào thư mục chỉ định."""
    # Tạo thư mục nếu chưa có
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Truy cập trang web
    driver.get(url)
    
    # Tùy chọn: Đợi một chút để trang load hoàn toàn trước khi chụp
    time.sleep(2)

    # Xác định tên file dùng timestamp để tránh trùng
    screenshot_filename = f"screenshot_{int(time.time())}.png"
    screenshot_path = os.path.join(download_dir, screenshot_filename)
    
    # Câu lệnh chụp và lưu screenshot
    driver.save_screenshot(screenshot_path)
    print(f"✅ Đã lưu screenshot thành công tại: {screenshot_path}")
    
    return screenshot_path


import os
uids = [
    'giang.tien.trung',
    '100005598214623',
    '100085462167190',
    '100005461662862',
    '100090647756824',
    '100073770454108',
    '100005180834862',
    '100091656182252',
    '100068953794888'
]
def run_selenium_task() -> str:
    """Main coordinator function for the Selenium task."""
    download_dir = "/app/downloads"
    url = "https://example.com"
    
    # 1. Initialize the bot with credentials (DO NOT create webdriver here)
    bot = FacebookBot(email="gurasyn@gmail.com", password="saile123456!")
    
    try:
        # 2. Trigger the smart login flow 
        # (This internally handles init_driver, cookie checks, and manual VNC fallback)
        bot.ensure_login()
        
        # 3. Quick validation: Check if the bot successfully acquired a driver session
        if bot.driver is None:
            print("❌ Halted: Bot could not establish a valid authenticated browser session.")
            return None
            
        # 4. Execute your custom logic (e.g., capture screenshot) using the active session
        print(f"📸 Navigating to task URL: {url}")
        path = capture_screenshot(bot.driver, url, download_dir)
        return path
        
    except Exception as e:
        print(f"❌ Error occurred during selenium task execution: {e}")
        return None
        
    finally:
        # 5. Always ensure the browser is closed to avoid RAM leaks
        # We use the built-in method inside your class
        bot.close_driver()