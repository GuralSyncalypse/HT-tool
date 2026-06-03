from fastapi import FastAPI, Request, HTTPException, Query
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
def get_groups(uid: str):
    data = redis_conn.get(f"groups:{uid}")
    if data:
        return json.loads(data)
    print("NONE")
    return []

@app.post("/run-bot")
def run_bot(req: BotRequest):
    
    # Lấy uid ra từ object req
    uid = req.uid
    
    # Lấy cookie từ Redis ra
    session_str = redis_conn.get(f"cookies:{uid}")
    
    # Thay vì return chuỗi error (dễ làm JS bị nhầm là thành công vì status vẫn là 200), 
    # hãy raise HTTPException 400 để Frontend nhảy vào block báo lỗi chuẩn xác.
    if not session_str:
        raise HTTPException(status_code=400, detail="Cookie hoặc User-Agent không tồn tại hoặc đã hết hạn")
        
    session_data = json.loads(session_str)
    # Chuyển ngược từ string thành list object trong Python
    user_cookies = session_data.get("cookies", [])
    user_agent = session_data.get("user_agent", "")
    
    job = queue.enqueue(run_selenium_task, {"uid": uid, "cookie_json": user_cookies, "user_agent": user_agent})
    
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