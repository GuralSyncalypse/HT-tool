import redis
import redis.asyncio as aioredis  # <-- Thêm thư viện này
import os
from sqlmodel import SQLModel, create_engine, Session

# 1. Cấu hình PostgreSQL
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5433/htland")
engine = create_engine(POSTGRES_URL, echo=False)

def init_db():
    # Tự động tạo các bảng nếu chưa có
    SQLModel.metadata.create_all(engine)

def get_db_session():
    # Dependency cung cấp session kết nối Postgres cho mỗi request
    with Session(engine) as session:
        yield session

# 2. Cấu hình Redis
redis_client = redis.Redis(
    host="redis", 
    port=6379, 
    db=0, 
    decode_responses=False
)

# 3. THÊM MỚI: Cấu hình Async Redis cho các endpoint FastAPI cần non-blocking
# Bật decode_responses=True để tự động decode thành string cho tiện xử lý JSON
async_redis_client = aioredis.Redis(
    host="redis",
    port=6379,
    db=0,
    decode_responses=True  
)