import os
import time
import random
import re
import redis
import json
from openpyxl import Workbook
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.remote.file_detector import LocalFileDetector

from sqlmodel import create_engine, Session, select
from models import User, UserRegister, UserResponse
from sqlalchemy.orm.attributes import flag_modified

POSTGRES_URL = "postgresql://postgres:admin@postgres_db:5432/htland"
engine = create_engine(POSTGRES_URL, echo=False)

# 1. Bật tính năng phát hiện file cục bộ
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Thư mục /app

# 1. Kết nối thẳng tới Redis từ file Selenium luôn
redis_conn = redis.Redis(host='redis', port=6379, decode_responses=True)
service = Service("/usr/bin/chromedriver")

class FacebookBot:
    def __init__(self):
        self.driver = None
        self.user_agent = None

        self.remote_url = os.getenv("SELENIUM_REMOTE_URL", "http://localhost:4444/wd/hub")

    def setup_driver(self):
        """Hàm phụ trách cấu hình và khởi tạo Chrome Driver"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless=new")  # Chạy ẩn trên background server
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={self.user_agent}")
        
        self.driver = webdriver.Remote(
            command_executor=self.remote_url,
            options=chrome_options
        )
        self.driver.file_detector = LocalFileDetector()

    def is_logged_in(self):
        driver = self.driver
        print(driver.get_cookies())
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
            
            success = self.is_logged_in()
            if success:
                print("Hoàn tất đăng nhập!")
            return success

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

    def scrape_joined_groups(self):
        """
        Hàm cào danh sách Group đã tham gia từ trang /groups/joins
        Chỉ tập trung tìm kiếm trong vùng nội dung chính (role="main")
        """
        print("🔄 Đang truy cập trang danh sách Nhóm đã tham gia...")
        self.driver.get("https://www.facebook.com/groups/joins")
        time.sleep(4) # Đợi trang tải các group đầu tiên

        # Vòng lặp cuộn trang để tải hết danh sách Group
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 10 
        
        for i in range(scroll_attempts):
            print(f"📜 Đang cuộn trang lần {i+1}/{scroll_attempts}...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) 
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("🛑 Đã cuộn đến cuối danh sách hoặc không có dữ liệu mới.")
                break
            last_height = new_height

        print("🔍 Bắt đầu trích xuất dữ liệu Group từ vùng nội dung chính...")
        joined_groups = []

        try:
            # 1. Định vị vùng nội dung chính của trang Facebook
            main_container = self.driver.find_element(By.XPATH, "//*[@role='main']")
            
            # 2. Chỉ tìm các khối group item NẰM TRONG vùng role="main" này
            group_items = main_container.find_elements(By.XPATH, ".//div[@role='listitem']")
            print(f"📊 Phát hiện {len(group_items)} khối group item trong khu vực nội dung chính.")

            for item in group_items:
                try:
                    # 3. Tìm thẻ <a> chứa link nhóm bên trong item
                    a_tag = item.find_element(By.XPATH, ".//a[contains(@href, '/groups/')]")
                    url = a_tag.get_attribute("href")
                    
                    # 4. Lấy tên Group (Xử lý fallback nếu thẻ a đầu tiên là ảnh/trống chữ)
                    title = a_tag.text.strip()
                    if not title:
                        all_links = item.find_elements(By.XPATH, ".//a[contains(@href, '/groups/')]")
                        for link in all_links:
                            if link.text.strip():
                                title = link.text.strip()
                                break

                    if title and url:
                        # Trích xuất ID/Alias từ URL
                        match = re.search(r'/groups/([^/]+)', url)
                        group_id = match.group(1) if match else None
                        
                        # Loại bỏ các sub-page mặc định
                        if not group_id or group_id in ["joins", "feed", "discover", "create"]:
                            continue

                        group_info = {
                            "group_name": title,
                            "group_id": group_id,
                            "group_url": f"https://www.facebook.com/groups/{group_id}/"
                        }
                        
                        # Kiểm tra trùng lặp theo ID
                        if not any(g['group_id'] == group_id for g in joined_groups):
                            print(f"✅ Đã tìm thấy: {title} (ID: {group_id})")
                            joined_groups.append(group_info)
                            
                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Không tìm thấy vùng nội dung chính (role='main'). Lỗi: {e}")
            return []

        print(f"🎉 Đã lọc và trích xuất thành công {len(joined_groups)} nhóm đã tham gia.")
        return joined_groups

    def create_post(self, content="", img_paths=[]):
        post_box_xpath = "//span[contains(text(),'mind') or contains(text(),'nghĩ gì') or contains(text(),'something') or contains(text(),'viết gì')]"

        post_box = self.driver.find_element(By.XPATH, post_box_xpath)
        post_box.click()

        print("Đã mở hộp đăng bài")

        time.sleep(2)

        composer = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@role='dialog' and @aria-modal='true']")
            )
        )

        print("Đã vào hộp đăng bài")

        # Cô lập Form
        editor = composer.find_element(
            By.XPATH,
            ".//div[@role='textbox']"
        )

        # 1. Tìm element cần điền

        editor.click()
        self.driver.execute_script("""
            var element = arguments[0];
            var text = arguments[1];
            
            // 1. Gán text (bao gồm cả Emoji) vào thẻ div
            element.innerText = text;
            
            // 2. Kích hoạt liên tiếp các sự kiện để React/Vue/Angular cập nhật State
            element.dispatchEvent(new Event('focus', { bubbles: true }));
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            element.dispatchEvent(new Event('blur', { bubbles: true }));
        """, editor, content)

        print("Đã nhập nội dung")

        # Thêm ảnh
        if not img_paths:
            print("Không tìm thấy ảnh!")
            return

        valid_file = 'image/*,image/heif,image/heic,video/*,video/mp4,video/x-m4v,video/x-matroska,.mkv,.avi,.wmv,.mov,.flv,.webm,.3gp,.3g2,.mts,.m2ts,.vob,.divx,.f4v,.ogv'
        file_input = composer.find_element(
            By.XPATH,
            f".//input[@accept='{valid_file}']"
        )
        
        for img_path in img_paths:
            file_name = img_path.split('\\')[-1]
            file_path = os.path.join(BASE_DIR, "bot_media_tmp", file_name)


            print(file_path)
            file_input.send_keys(file_path)

        
        time.sleep(1)
        #
        post_btn = composer.find_element(
            By.XPATH,
            ".//div[@aria-label='Post']"
        )

        #post_btn.click()
        print("Đã đăng bài!")


    def run_actions(self, uid: str, content="", img_paths=[]):
        """Hàm chứa các kịch bản hành động của bot sau khi đã login thành công"""
        if not self.driver:
            print(f"[UID: {uid}] Trình duyệt chưa được khởi tạo!")
            return
            
        try:
            print(f"[UID: {uid}] Đang thực hiện các tác vụ của bot...")
            # Ví dụ các hành động của bạn:
            
            # data = []
            # for uid in uids:
            #     success = self.send_message_via_uid(uid, "Hello!")
            #     data.append([uid, success])
            
            # groups = self.scrape_joined_groups()
            # print(groups)
            # try:
            #     redis_conn.set(f"groups:{uid}", json.dumps(groups))
            #     print(f"🚀 [Worker] Đã lưu thẳng {len(groups)} group vào Redis cho UID {uid}!")
            # except Exception as redis_err:
            #     print(f"❌ Lỗi ghi Redis từ Worker: {redis_err}")

            self.driver.get('https://www.facebook.com/groups/502928924130697')
            self.create_post(content, img_paths)

            self.driver.get('https://www.facebook.com/groups/quantanbin')
            self.create_post(content, img_paths)

            time.sleep(5) # Giả lập thời gian bot làm việc
            # create_excel_file(data, ['uid', 'success'], 'app/output', 'result.xlsx')
            
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

def create_excel_file(data, headers, dir, filename):
    if not os.path.exists(dir):
        os.makedirs(dir)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Results"

    # Headers
    ws.append(headers)

    # Data rows
    for row in data:
        ws.append(row)

    full_path = dir + '/' + filename

    wb.save(full_path)

    print(f"Excel file '{full_path}' created successfully.")


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

def run_selenium_scan_group(data: dict):
    uid = data.get("uid")
    username = data.get("username")

    bot = FacebookBot()
    bot.user_agent = data.get("user_agent", "")


    try:
        # 2. Đăng nhập
        if not bot.login_with_cookies(uid, data.get("cookie_json", [])):
            print("Failed login!")
            return {"status": "failed", "reason": "auth_failed", "uid": uid}

        # 3. Điều phối tác vụ (Rẽ nhánh gọi hàm riêng biệt)
        groups = bot.scrape_joined_groups()
        print(groups)

        with Session(engine) as session:
            # 1. Tìm User trong DB dựa vào UID (ở đây giả định cột username lưu UID)
            statement = select(User).where(User.username == username)
            user = session.exec(statement).first()
            
            if user:
                # 2. Cập nhật mảng nhóm mới cào được vào trường JSONB
                if uid not in user.social_data:
                    user.social_data[uid] = {
                        "group_uids": [],
                        "friend_uids": []
                    }

                user.social_data[uid]["group_uids"] = groups

                flag_modified(user, "social_data")

                session.add(user)
                session.commit()
                print(f"🚀 [Worker] Đã lưu {len(groups)} groups vào Postgres JSONB cho UID {uid}!")
            else:
                print(f"❌ Không tìm thấy User có UID {uid} trong Database để lưu groups")

        return {"status": "completed", "uid": uid}

    except Exception as e:
        print(f"[Task {uid}] Lỗi hệ thống: {str(e)}")
        return {"status": "error", "message": str(e), "uid": uid}

    finally:
        bot.close()

def run_selenium_task(data: dict):
    uid = data.get("uid")
    action = data.get("action")
    imgs_path = data.get("image_paths", [])

    # 1. Khởi tạo Bot và cấu hình
    bot = FacebookBot()
    bot.user_agent = data.get("user_agent", "")

    try:
        # 2. Đăng nhập
        if not bot.login_with_cookies(uid, data.get("cookie_json", [])):
            print("Failed login!")
            return {"status": "failed", "reason": "auth_failed", "uid": uid}

        # 3. Điều phối tác vụ (Rẽ nhánh gọi hàm riêng biệt)
        execute_action_routing(bot, action, data)

        return {"status": "completed", "uid": uid}

    except Exception as e:
        print(f"[Task {uid}] Lỗi hệ thống: {str(e)}")
        return {"status": "error", "message": str(e), "uid": uid}

    finally:
        # 4. Giải phóng tài nguyên (Bắt buộc)
        bot.close()
        clean_temporary_images(imgs_path, uid)

def clean_temporary_images(imgs_path: list, uid: str):
    """Hàm chuyên trách dọn dẹp các file ảnh tạm trên đĩa cứng"""
    if not imgs_path:
        return

    print(f"[Task {uid}] Bắt đầu dọn dẹp {len(imgs_path)} file ảnh tạm.")
    for path in imgs_path:
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"-> Đã xóa file thành công: {path}")
        except Exception as e:
            # Chỉ log lại lỗi chứ không hoãn tiến trình (không raise error ở đây)
            print(f"-> Không thể xóa file {path}. Lỗi: {str(e)}")


def execute_action_routing(bot: FacebookBot, action: str, data: dict):
    """Hàm chuyên trách việc đọc action và phân phối công việc cho Bot"""
    uid = data.get("uid")
    content = data.get("text_content", "")
    imgs_path = data.get("image_paths", [])

    print(f"[Task {uid}] Đang xử lý action: '{action}'")

    if action == "update-group":
        groups = bot.scrape_joined_groups()
        print(groups)
        try:
            redis_conn.set(f"groups:{uid}", json.dumps(groups))
            print(f"🚀 [Worker] Đã lưu thẳng {len(groups)} group vào Redis cho UID {uid}!")
        except Exception as redis_err:
            print(f"❌ Lỗi ghi Redis từ Worker: {redis_err}")
        
        
    elif action == "comment_spam":
        target_urls = data.get("target_urls", [])
        bot.comment_to_targets(target_urls, content)
        
    else:
        raise ValueError(f"Action '{action}' không hợp lệ hoặc chưa được hỗ trợ.")