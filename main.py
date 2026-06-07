import json
import os
import time
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from sqlmodel import Session, select
from contextlib import asynccontextmanager

# Modules nội bộ (Tự tạo)
from database import get_db_session, init_db, redis_client
from models import GroupDetail, SocialAccount, User, UserRegister, UserResponse
from security import create_access_token, decode_access_token, hash_password, verify_password
from tasks import run_selenium_scan_group, run_selenium_task

# 1. Thay thế cho @app.on_event("startup") đã bị khai tử
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Hành động khi ứng dụng BẮT ĐẦU chạy
    init_db()
    yield
    # Hành động khi ứng dụng DỪNG (nếu có, ví dụ: đóng kết nối DB, ngắt kết nối Redis)
    pass

# Khởi tạo app với lifespan
app = FastAPI(lifespan=lifespan)

# 2. Cấu hình Middleware (Cần lưu ý khi lên Production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Xem lưu ý bảo mật bên dưới
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount thư mục chứa file tĩnh (Đảm bảo thư mục "static" đã tồn tại)
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# Cấu hình OAuth2 chuẩn để test được trên giao diện /docs của FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

templates = Jinja2Templates(directory="templates")

redis_conn = Redis(host="localhost", port=6379)
queue = Queue(connection=redis_conn)


class CookieData(BaseModel):
    uid: str
    cookie_json: list
    user_agent: str

class BotRequest(BaseModel):
    uid: str

class PaginatedGroupResponse(BaseModel):
    total: int
    data: List[GroupDetail]

# Tạo thư mục lưu ảnh tạm thời trên server nếu chưa có
UPLOAD_DIR = "./bot_media_tmp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Endpoint nhận danh sách groups
@app.post("/api/groups/process")
def process_user_groups(
    groups: List[GroupDetail], 
):
    print(f"Nhận được {len(groups)} groups gửi lên từ frontend.")
    
    # Xử lý logic của bạn ở đây (Vòng lặp lưu DB hoặc kích hoạt Bot...)
    for group in groups:
        print(f"Đang xử lý Group ID: {group.group_id} - Name: {group.group_name}")
        
    return {"status": "success", "message": f"Đã xử lý {len(groups)} nhóm thành công"}

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

@app.get("/api/get-groups", response_model=PaginatedGroupResponse)
def get_groups(
    uid: str,
    username: str, 
    page: int = 1, 
    page_size: int = 10, 
    db: Session = Depends(get_db_session)
):
    # 1. Tìm account dựa trên uid và username
    statement = select(SocialAccount).where(
        SocialAccount.uid == uid,
        SocialAccount.username == username
    )
    account = db.exec(statement).first()
    
    # Nếu không tìm thấy account, trả về total = 0 và mảng rỗng đúng cấu trúc
    if not account:
        return {"total": 0, "data": []}

    # 2. Lấy toàn bộ mảng từ trường JSONB
    all_groups = account.groups_data or []
    
    # 3. Lấy TỔNG SỐ LƯỢNG phần tử có trong mảng JSONB này
    total_count = len(all_groups)

    # 4. Phân trang bằng kỹ thuật Slice của Python
    offset = (page - 1) * page_size
    paginated_groups = all_groups[offset : offset + page_size]

    # 5. Trả về đúng cấu trúc như Schema đã khai báo
    return {
        "total": total_count,
        "data": paginated_groups
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    return {
        "filename": file.filename,
        "content_type": file.content_type
    }

# --- 1. API ĐĂNG KÝ TÀI KHOẢN (LƯU TEXT THUẦN) ---
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db_session)):
    statement = select(User).where((User.username == user_in.username) | (User.email == user_in.email))
    user_exists = db.exec(statement).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Username hoặc Email đã được đăng ký.")
    
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password) # Mật khẩu đã được mã hóa an toàn
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- 2. API ĐĂNG NHẬP (TRẢ VỀ TOKEN THUẦN) ---
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db_session)):
    user = db.exec(select(User).where(User.username == form_data.username)).first()
    
    # Xác thực mật khẩu bằng Bcrypt
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản của bạn đang bị khóa")

    # Tạo JWT token ngẫu nhiên theo thời gian
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- 3. KIỂM TRA ĐIỀU KIỆN TOKEN QUA REDIS BLACKLIST ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db_session)) -> User:
    # Bước 1: Check xem token mã hóa này có nằm trong Blacklist của Redis không
    print("ACC")
    if redis_client.get(f"blacklist:{token}"):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập đã đăng xuất. Vui lòng login lại.")
    
    # Bước 2: Giải mã Token để lấy username bên trong payload
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
        
    # Bước 3: Tìm nốt thông tin User trong PostgreSQL
    user = db.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
    return user

# --- 4. API LẤY THÔNG TIN CÁ NHÂN ---
@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    print(current_user)
    return current_user

# --- 5. API ĐĂNG XUẤT (LƯU VÀO REDIS) ---
@app.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    # Đưa chuỗi mã hóa token độc nhất của phiên này vào Redis Blacklist trong 30 phút
    redis_client.setex(name=f"blacklist:{token}", time=1800, value="blacklisted")
    return {"message": "Đăng xuất thành công"}


@app.post("/bot/scan-group")
async def scan_group(uid: str = Form(...), username: str = Form(...)):
    session_str = redis_conn.get(f"cookies:{uid}")
    if not session_str:
        raise HTTPException(status_code=400, detail="Tài khoản chưa đăng nhập hoặc cookie hết hạn")
    
    session_data = json.loads(session_str)

    # 3. Đóng gói dữ liệu bài viết chuyển giao cho Hàng đợi (Queue)
    task_data = {
        "username": username,
        "uid": uid,
        "cookie_json": session_data.get("cookies", []),
        "user_agent": session_data.get("user_agent", ""),
    }

    # Đẩy sang Worker thông qua hàng đợi
    job = queue.enqueue(run_selenium_scan_group, task_data)
    
    return {"status": "queued", "job_id": job.id}

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

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.get("/register", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )

@app.post("/test-post")
async def receive_url(data: dict):
    print(data)

    return {"success": True}