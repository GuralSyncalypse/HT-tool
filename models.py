from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

# Now you can call them directly without the prefix
vnTimeDelta = timedelta(hours=7)
vnTZObject = timezone(vnTimeDelta, name="ICT")

# Schema Pydantic cho từng Group (Giữ nguyên)
class GroupDetail(BaseModel):
    group_id: str
    group_url: str
    group_name: str

    class Config:
        from_attributes = True

# --- BẢNG USER (Đã tinh giản social_data) ---
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, nullable=False)
    email: str = Field(unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Thiết lập mối quan hệ để dễ dàng gọi user.social_accounts nếu cần
    social_accounts: List["SocialAccount"] = Relationship(back_populates="user")


# --- BẢNG MỚI: TÀI KHOẢN MẠNG XÃ HỘI (UID) ---
class SocialAccount(SQLModel, table=True):
    __tablename__ = "social_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    uid: str = Field(unique=True, index=True, nullable=False)  # Ví dụ: "61573394223842"
    username: Optional[str] = Field(default=None)             # Tên Facebook cá nhân của UID đó
    cookie: Optional[str] = Field(default=None)               # Lưu cookie để worker bóc tách dữ liệu
    is_live: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Khóa ngoại liên kết tới bảng Users chính
    user_id: int = Field(foreign_key="users.id", nullable=False)
    user: User = Relationship(back_populates="social_accounts")

    # Lưu danh sách nhóm của RIÊNG UID này thẳng vào mảng JSON
    groups_data: List[GroupDetail] = Field(
        default=[], 
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

    # Thiết lập mối quan hệ để dễ dàng gọi user.social_accounts nếu cần
    social_accounts: List["SocialAccount"] = Relationship(back_populates="user")