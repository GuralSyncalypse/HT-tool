from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import requests
from typing import Dict, List, Any
from redis import Redis
from rq import Queue
from tasks import run_selenium_task
from pydantic import BaseModel
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

templates = Jinja2Templates(directory="templates")

redis_conn = Redis(host="localhost", port=6379)
queue = Queue(connection=redis_conn)


class CookieData(BaseModel):
    uid: str
    cookie_json: list

@app.get("/api/active-accounts")
def get_active_accounts():
    cookie_keys = redis_conn.keys("cookies:*")
    uids = [key.decode('utf-8').split(":")[1] for key in cookie_keys]
    return {"uids": uids}

@app.post("/api/cookies")
def save_cookie(data: CookieData):
    # Chuyển list cookie thành chuỗi json string để lưu vào Redis
    cookie_str = json.dumps(data.cookie_json)
    
    print(cookie_str)
    # Lưu vào redis với Key là "cookies:{uid}"
    # Set thời gian hết hạn (ví dụ: 86400 giây = 1 ngày), hết 1 ngày redis tự xóa cho sạch RAM
    redis_conn.set(f"cookies:{data.uid}", cookie_str, ex=86400)
    
    return {"status": "Đã lưu vào Redis thành công", "uid": data.uid}

# 1. Tạo một class định nghĩa cấu trúc dữ liệu JSON gửi lên
class BotRequest(BaseModel):
    uid: str

# 2. Sửa tham số truyền vào hàm thành req: BotRequest
@app.post("/run-bot")
def run_bot(req: BotRequest):  # <--- Thay đổi ở đây
    
    # Lấy uid ra từ object req
    uid = req.uid
    
    # Lấy cookie từ Redis ra
    cookie_str = redis_conn.get(f"cookies:{uid}")
    print(cookie_str)
    
    # Thay vì return chuỗi error (dễ làm JS bị nhầm là thành công vì status vẫn là 200), 
    # hãy raise HTTPException 400 để Frontend nhảy vào block báo lỗi chuẩn xác.
    if not cookie_str:
        raise HTTPException(status_code=400, detail="Cookie không tồn tại hoặc đã hết hạn")
        
    # Chuyển ngược từ string thành list object trong Python
    user_cookies = json.loads(cookie_str)
    
    # Đẩy vào queue cho Selenium chạy
    job = queue.enqueue(run_selenium_task, {"uid": uid, "cookie_json": user_cookies})
    
    return {"status": "queued", "job_id": job.id}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    data_from_db = [
        {"id": "vip", "name": "Tài khoản VIP"},
        {"id": "normal", "name": "Tài khoản Thường"}
    ]
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request, 
            "account_list": data_from_db
        }
    )

@app.post("/test-post")
async def receive_url(data: dict):
    print(data)

    return {"success": True}

@app.post("/store-cookies")
async def store_cookies(data: CookieData):
    print(f"Nhận được cookie của UID: {data.uid}")
    print(f"Chuỗi Cookie: {data.cookie_string[:50]}...") # In thử một đoạn ngắn tránh lộ
    
    # TÙY CHỌN: Bạn có thể test thử xem cookie này có hoạt động hay không bằng cách gọi thử vào FB
    #test_fb_connection(data.cookie_json)
    
    return {"status": "success", "message": f"Đã lưu cookie cho tài khoản {data.uid}"}


def test_fb_connection(cookies_dict):
    """Hàm bổ trợ: Thử dùng cookie vừa nhận để lấy trang chủ FB bằng Python requests"""
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get("https://mbasic.facebook.com/", cookies=cookies_dict, headers=headers)
    if "mbasic_logout_button" in response.text:
        print("=> Cookie hoạt động tốt (Đã login thành công từ phía Backend)!")
    else:
        print("=> Cookie die hoặc không hợp lệ.")