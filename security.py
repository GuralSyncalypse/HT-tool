import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from fastapi import HTTPException, status

# Thay thế CryptContext của passlib bằng PasswordHash của pwdlib
PWD_CONTEXT = PasswordHash((BcryptHasher(),))

# Khóa bí mật để ký JWT (Trong thực tế nên để ở file .env)
SECRET_KEY = "SIEUBAOMAT_123457" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token có hiệu lực trong 30 phút

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu thành chuỗi hash không thể dịch ngược"""
    # pwdlib xử lý trực tiếp chuỗi str, loại bỏ hoàn toàn việc encode/decode bytes cồng kềnh cũ
    hashed = PWD_CONTEXT.hash(password)
    print(hashed)
    return hashed

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu người dùng nhập vào với chuỗi hash trong DB"""
    return PWD_CONTEXT.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    """Tạo mã JWT Access Token mã hóa ngẫu nhiên chứa thông tin user"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Giải mã và kiểm tra tính hợp lệ của Token từ client gửi lên"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ hoặc đã bị thay đổi")