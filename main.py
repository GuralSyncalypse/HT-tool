# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from database import init_db
# Import các router con
from routers.views import router as views_router
from routers.auth import router as auth_router
from routers.groups import router as groups_router
from routers.bot import router as bot_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo DB khi ứng dụng chạy
    init_db()
    yield
    # Giải phóng tài nguyên khi tắt ứng dụng (Nếu có)
    pass

app = FastAPI(
    title="Hệ thống Automation Bot Server",
    version="1.0.0",
    lifespan=lifespan
)

# Cấu hình Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Khuyến nghị thay đổi thành Domain cụ thể khi lên Production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thư mục tĩnh
app.mount("/static", StaticFiles(directory="static"), name="static")

# ĐĂNG KÝ ROUTER VÀO HỆ THỐNG
# 1. Router giao diện (Không dùng prefix)
app.include_router(views_router)

# 2. Các API Logic (Gom cụm bằng tiền tố chung hệ thống /api/v1)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(groups_router, prefix="/api/v1")
app.include_router(bot_router, prefix="/api/v1")