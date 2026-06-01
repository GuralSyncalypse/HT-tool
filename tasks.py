from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import os  # Thêm thư viện os để quản lý đường dẫn file

def run_selenium_task():
    options = Options()
    options.add_argument("--headless")           # Chạy ẩn, không cần màn hình
    options.add_argument("--no-sandbox")          # Bắt buộc khi chạy quyền root trong Docker
    options.add_argument("--disable-dev-shm-usage") # Tránh tràn bộ nhớ đệm /dev/shm của container
    
    # options.add_argument("--window-size=1920,1080")  # Tùy chọn: Đặt kích thước màn hình để screenshot đẹp hơn

    options.binary_location = "/usr/bin/chromium"

    # --- CẤU HÌNH THƯ MỤC LƯU SCREENSHOT ---
    # File sẽ được lưu tạm thời vào thư mục /app/downloads bên trong container
    # (Thư mục này được mount ra máy host thông qua Docker Volume)
    download_dir = "/app/downloads"
    
    # Tạo thư mục nếu chưa có
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://example.com")
        
        # Tùy chọn: Đợi một chút để trang load hoàn toàn trước khi chụp
        time.sleep(2)

        title = driver.title
        
        # --- LƯU SCREENSHOT ---
        # Xác định tên file, ví dụ dùng timestamp để tránh trùng
        screenshot_filename = f"screenshot_{int(time.time())}.png"
        screenshot_path = os.path.join(download_dir, screenshot_filename)
        
        # Câu lệnh chụp và lưu screenshot
        driver.save_screenshot(screenshot_path)
        print(f"✅ Đã lưu screenshot thành công tại: {screenshot_path}")

        # Bạn có thể trả về đường dẫn file ảnh thay vì title
        return screenshot_path 
    except Exception as e:
        print(f"❌ Có lỗi xảy ra khi chụp ảnh: {e}")
        return None
    finally:
        driver.quit()