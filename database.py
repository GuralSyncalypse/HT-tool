import redis
from sqlmodel import SQLModel, create_engine, Session

# 1. Cấu hình PostgreSQL
POSTGRES_URL = "postgresql://postgres:admin@localhost:5433/htland"
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
    host="localhost", 
    port=6379, 
    db=0, 
    decode_responses=False  # Tự động decode bytes thành chuỗi string string cho dễ dùng
)