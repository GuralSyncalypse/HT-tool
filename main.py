import time
from fastapi import FastAPI, Request, HTTPException, Query, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from typing import Dict, List, Any
from redis import Redis
from rq import Queue
from tasks import run_selenium_task
from pydantic import BaseModel
import json
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")

redis_conn = Redis(host="localhost", port=6379)
queue = Queue(connection=redis_conn)


class GroupInfo(BaseModel):
    group_name: str
    group_id: str
    group_url: str

class CookieData(BaseModel):
    uid: str
    cookie_json: list
    user_agent: str

class BotRequest(BaseModel):
    uid: str

# Tạo thư mục lưu ảnh tạm thời trên server nếu chưa có
UPLOAD_DIR = "./bot_media_tmp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/api/active-accounts")
def get_active_accounts():
    cookie_keys = redis_conn.keys("cookies:*")
    uids = [key.decode('utf-8').split(":")[1] for key in cookie_keys]
    return {"uids": uids}

@app.post("/api/cookies")
def save_cookie(data: CookieData):
    # 1. Đóng gói cả cookie và user_agent vào một Dictionary
    session_data = {
        "cookies": data.cookie_json,
        "user_agent": data.user_agent
    }
    
    # 2. Chuyển toàn bộ object trên thành chuỗi JSON string
    session_str = json.dumps(session_data)
    
    print(session_data['cookies'])

    # Lưu vào redis với Key là "cookies:{uid}"
    # Set thời gian hết hạn (ví dụ: 86400 giây = 1 ngày), hết 1 ngày redis tự xóa cho sạch RAM
    redis_conn.set(f"cookies:{data.uid}", session_str, ex=86400)
    
    return {"status": "Đã lưu vào Redis thành công", "uid": data.uid}

@app.get("/api/get-groups/{uid}")
def get_groups(uid: str, page: int = 1, page_size: int = 10):
    data = redis_conn.get(f"groups:{uid}")
    if data:
        return json.loads(data)
    return []

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    print(file)
    return {
        "filename": file.filename,
        "content_type": file.content_type
    }

@app.post("/run-bot")
async def run_bot(
    uid: str = Form(...),
    action: str = Form(...),
    content: str = Form(""),
    images: List[UploadFile] = File(default=[])
):
    # 1. Lấy Token/Cookie của UID này từ Redis ra
    print(content)
    print(images)
    session_str = redis_conn.get(f"cookies:{uid}")
    if not session_str:
        raise HTTPException(status_code=400, detail="Tài khoản chưa đăng nhập hoặc cookie hết hạn")
    
    session_data = json.loads(session_str)
    
    # 2. Xử lý lưu ảnh nhị phân thành file vật lý
    saved_paths = []
    for index, img in enumerate(images):
        ext = os.path.splitext(img.filename)[1] # Lấy đuôi file (.jpg, .png...)
        filename = f"task_{uid}_{int(time.time())}_{index}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Đọc file từ bộ nhớ tạm và ghi xuống đĩa cứng
        content_binary = await img.read()
        with open(file_path, "wb") as f:
            f.write(content_binary)
            
        # Lấy đường dẫn tuyệt đối (Ví dụ: D:/project/bot_media_tmp/task_100_1.jpg)
        saved_paths.append(os.path.abspath(file_path))

    
    # 3. Đóng gói dữ liệu bài viết chuyển giao cho Hàng đợi (Queue)
    task_data = {
        "uid": uid,
        "cookie_json": session_data.get("cookies", []),
        "user_agent": session_data.get("user_agent", ""),
        "action": action,
        "text_content": content,
        "image_paths": saved_paths  # Danh sách các đường dẫn ảnh trên server
    }
    
    # Đẩy sang Worker thông qua hàng đợi (Redis Queue / Celery)
    job = queue.enqueue(run_selenium_task, task_data)
    
    return {"status": "queued", "job_id": job.id, "images_received": len(saved_paths)}

@app.post("/scan-groups")
async def run_group_scan(uid: str = Form(...)): # Nên chuyển sang Form cho đồng bộ với bot
    # 1. Kiểm tra spam: Nếu UID này đang có task quét chạy rồi thì chặn lại
    is_scanning = redis_conn.get(f"scanning_lock:{uid}")
    if is_scanning:
        raise HTTPException(status_code=429, detail="Hệ thống đang quét nhóm cho tài khoản này, vui lòng đợi")

    session_str = redis_conn.get(f"cookies:{uid}")
    if not session_str:
        raise HTTPException(status_code=400, detail="Tài khoản chưa đăng nhập")
    session_data = json.loads(session_str)
    
    # Khóa tạm thời trong Redis (hết hạn sau 5 phút nếu lỗi hệ thống xảy ra)
    redis_conn.setex(f"scanning_lock:{uid}", 300, "true")
    
    # 2. Đồng nhất cấu trúc Payload gửi qua Worker giống endpoint trên
    task_data = {
        "uid": uid,
        "cookie_json": session_data.get("cookies", []),
        "user_agent": session_data.get("user_agent", ""),
        "action": "scan_groups",
        "text_content": "",
        "image_paths": []
    }
    
    job = queue.enqueue(run_selenium_task, task_data)
    return {"status": "queued", "job_id": job.id}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

@app.post("/test-post")
async def receive_url(data: dict):
    print(data)

    return {"success": True}