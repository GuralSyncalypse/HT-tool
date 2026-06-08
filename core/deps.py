# core/deps.py
import json
from typing import Any, Dict
from fastapi import HTTPException
from database import redis_client # Hoặc biến kết nối redis của bạn

def get_user_session(uid: str) -> Dict[str, Any]:
    session_str = redis_client.get(f"cookies:{uid}")
    if not session_str:
        raise HTTPException(
            status_code=400, 
            detail="Tài khoản chưa đăng nhập hoặc cookie hết hạn"
        )
    try:
        return json.loads(session_str)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, 
            detail="Dữ liệu session không hợp lệ"
        )