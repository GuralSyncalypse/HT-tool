# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select

from database import get_db_session, redis_client
from models import User, UserRegister, UserResponse
from security import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/login") # Cập nhật lại đường dẫn Swagger chuẩn

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db_session)) -> User:
    if redis_client.get(f"blacklist:{token}"):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập đã hết hạn. Vui lòng login lại.")
    
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
        
    user = db.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db_session)):
    statement = select(User).where((User.username == user_in.username) | (User.email == user_in.email))
    if db.exec(statement).first():
        raise HTTPException(status_code=400, detail="Username hoặc Email đã được đăng ký.")
    
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db_session)):
    user = db.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản của bạn đang bị khóa")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    redis_client.setex(name=f"blacklist:{token}", time=1800, value="blacklisted")
    return {"message": "Đăng xuất thành công"}