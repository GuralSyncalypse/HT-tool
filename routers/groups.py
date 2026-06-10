# routers/groups.py
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlmodel import select
from sqlalchemy.orm import Session

from database import get_db_session, redis_client  
from models import GroupDetail, SocialAccount

router = APIRouter(tags=["Data Processing"])

class CookieData(BaseModel):
    uid: str
    cookie_json: list
    user_agent: str

class PaginatedGroupResponse(BaseModel):
    total: int
    data: List[GroupDetail]

@router.post("/groups/process")
def process_user_groups(groups: List[GroupDetail]):
    for group in groups:
        # Xử lý logic nghiệp vụ lưu DB tại đây
        pass
    return {"status": "success", "message": f"Đã xử lý {len(groups)} nhóm thành công"}

@router.get("/active-accounts")
def get_active_accounts(db: Session = Depends(get_db_session)):
    # 1. Quét Redis lấy danh sách UID (Giữ nguyên logic gốc của bạn)
    cookie_keys = redis_client.keys("cookies:*")
    active_uids = [key.decode('utf-8').split(":")[1] for key in cookie_keys]
    
    if not active_uids:
        # Trả về cả 2 định dạng trống để không bên nào bị crash
        return {"uids": [], "accounts": {}}
        
    # 2. Query vào DB để tìm Username tương ứng
    statement = select(SocialAccount).where(SocialAccount.uid.in_(active_uids))
    accounts = db.exec(statement).all()
    
    # Map UID -> Username
    account_mapping = {acc.uid: acc.username for acc in accounts}
    for uid in active_uids:
        if uid not in account_mapping:
            account_mapping[uid] = "unknown"
    
    print(account_mapping)
    # 3. TRẢ VỀ CẢ HAI: Vừa có 'uids' cho tác vụ cũ, vừa có 'accounts' cho Odoo
    return {
        "uids": active_uids,               # <--- Tác vụ cũ dùng cái này (Dạng List)
        "accounts": account_mapping        # <--- Odoo dùng cái này (Dạng Dict)
    }

@router.post("/cookies")
def save_cookie(data: CookieData):
    session_data = {"cookies": data.cookie_json, "user_agent": data.user_agent}
    redis_client.set(f"cookies:{data.uid}", json.dumps(session_data), ex=86400)
    return {"status": "Đã lưu vào Redis thành công", "uid": data.uid}

@router.get("/get-groups", response_model=PaginatedGroupResponse)
def get_groups(
    uid: str, 
    username: str, 
    page: Optional[int] = None,       # Chuyển thành Optional
    page_size: Optional[int] = None,  # Chuyển thành Optional
    db: Session = Depends(get_db_session)
):
    # 1. Kiểm tra tài khoản
    account = db.exec(
        select(SocialAccount).where(
            SocialAccount.uid == uid, 
            SocialAccount.username == username
        )
    ).first()
    
    if not account:
        return {"total": 0, "data": []}

    all_groups = account.groups_data or []
    total_count = len(all_groups)

    # 2. KIỂM TRA LOGIC DÙNG CHUNG: 
    # Nếu không truyền page hoặc page_size (như khi Odoo gọi), trả về TẤT CẢ các group
    if page is None or page_size is None:
        return {
            "total": total_count,
            "data": all_groups
        }

    # 3. Nếu có truyền page và page_size (UI Paginator đang gọi), xử lý phân trang như cũ
    offset = (page - 1) * page_size
    return {
        "total": total_count,
        "data": all_groups[offset : offset + page_size]
    }

@router.get("/get-group-ids", response_model=List[str])
def get_group_ids(uid: str, username: str, db: Session = Depends(get_db_session)):
    # 1. Tìm tài khoản trong database
    account = db.exec(
        select(SocialAccount).where(
            SocialAccount.uid == uid, 
            SocialAccount.username == username
        )
    ).first()
    
    # 2. Nếu không thấy tài khoản, trả về mảng rỗng ngay lập tức
    if not account or not account.groups_data:
        return []

    # 3. Chỉ trích xuất phần group_id ra một mảng phẳng
    # Xử lý an toàn cho cả trường hợp g là dict hoặc g là object
    group_ids = [
        g.get("group_id") if isinstance(g, dict) else getattr(g, "group_id", "")
        for g in account.groups_data
    ]
    
    # Lọc bỏ các giá trị rỗng nếu có rác trong data
    return [gid for gid in group_ids if gid]

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename, "content_type": file.content_type}

@router.post("/test-post")
async def receive_url(data: dict):
    return {"success": True}