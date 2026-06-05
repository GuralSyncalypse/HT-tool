from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, Dict
from datetime import datetime

# Bảng lưu trong PostgreSQL
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, nullable=False)
    email: str = Field(unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Lưu thông tin Groups
    social_data: Dict[str, Dict[str, List[str]]] = Field(
        default={}, 
        sa_column=Column(JSONB, nullable=False)
    )

# Schema nhận dữ liệu đăng ký từ Client
class UserRegister(SQLModel):
    username: str
    email: str
    password: str

# Schema trả về thông tin User (Ẩn hashed_password đi để bảo mật)
class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    is_active: bool

    # Lưu thông tin Groups
    social_data: Dict[str, Dict[str, List[str]]] = Field(
        default={}, 
        sa_column=Column(JSONB, nullable=False)
    )