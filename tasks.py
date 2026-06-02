import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

service = Service("/usr/bin/chromedriver")
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

class FacebookBot:
    def __init__(self):
        self.driver = None
        self.remote_url = os.getenv("SELENIUM_REMOTE_URL", "http://localhost:4444/wd/hub")

    def setup_driver(self):
        """Hàm phụ trách cấu hình và khởi tạo Chrome Driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Chạy ẩn trên background server
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        #chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Remote(
            command_executor=self.remote_url,
            options=chrome_options
        )

    def is_logged_in(self):
        driver = self.driver

        cookies = {c["name"] for c in driver.get_cookies()}

        # Fast fail
        if "c_user" not in cookies or "xs" not in cookies:
            return False

        # Verify session
        driver.get("https://www.facebook.com/me")

        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        return True

    def login_with_cookies(self, uid: str, cookies: list) -> bool:
        """
        Hàm chính phụ trách mở browser, inject cookies để đăng nhập vào Facebook
        Trả về True nếu thành công, False nếu thất bại.
        """
        print(f"[UID: {uid}] Đang khởi tạo trình duyệt...")
        self.setup_driver()

        print("ABC")
        
        try:
            # 1. Đi tới Facebook trước khi add cookie
            self.driver.get("https://www.facebook.com")
            time.sleep(2)        

            allowed = {
                "name",
                "value",
                "domain",
                "path",
                "expiry",
                "secure",
                "httpOnly"
            }

            for cookie in cookies:
                cookie = {k: v for k, v in cookie.items() if k in allowed}
                try:
                    print(f"Adding {cookie}")
                    self.driver.add_cookie(cookie)
                except:
                    print(f'Failed: {cookie}')
            
            # 3. Refresh để áp dụng Cookie và vào trạng thái Đăng Nhập
            self.driver.refresh()
            time.sleep(3)
            
            print(f"[UID: {uid}] Inject cookie hoàn tất. Tiêu đề trang: {self.driver.title}")
            return True

        except Exception as e:
            print(f"[UID: {uid}] Gặp lỗi trong quá trình inject cookie: {e}")
            self.close() # Đóng driver ngay nếu lỗi giữa chừng
            return False

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

    def run_actions(self, uid: str):
        """Hàm chứa các kịch bản hành động của bot sau khi đã login thành công"""
        if not self.driver:
            print(f"[UID: {uid}] Trình duyệt chưa được khởi tạo!")
            return
            
        try:
            print(f"[UID: {uid}] Đang thực hiện các tác vụ của bot...")
            # Ví dụ các hành động của bạn:
            
            for uid in uids:
                self.send_message_via_uid(uid, "Hello!")

            time.sleep(5) # Giả lập thời gian bot làm việc
            
        except Exception as e:
            print(f"[UID: {uid}] Lỗi khi chạy tác vụ: {e}")

    def close(self):
        """Đóng trình duyệt giải phóng RAM"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("Đã đóng trình duyệt an toàn.")

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

# Hàm này được gọi bởi queue.enqueue(run_selenium_task, data)
def run_selenium_task(data: dict):
    uid = data.get("uid")
    cookies = data.get("cookie_json", [])
    
    # 1. Khởi tạo đối tượng Bot từ Class
    bot = FacebookBot()
    
    # 2. Gọi hàm login bằng cookie
    login_success = bot.login_with_cookies(uid, cookies)
    
    if login_success:
        # 3. Chạy kịch bản nuôi tài khoản/spam/tương tác nếu login thành công
        bot.run_actions(uid)
        
    # 4. LUÔN LUÔN đóng bot ở cuối cùng để tránh tràn RAM server
    bot.close()
    
    return {"status": "completed", "uid": uid}


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