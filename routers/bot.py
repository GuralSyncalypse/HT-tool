# routers/bot.py
import os
import uuid
import json
import aiofiles
import asyncio
from typing import List
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Body, Depends, Request
from rq import Queue
from rq.registry import StartedJobRegistry
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus

from core.deps import get_user_session
from tasks import run_selenium_scan_group, run_selenium_task

from database import get_db_session, redis_client, async_redis_client
from sqlmodel import Session, select
from models import SocialAccount
from security import verify_odoo_hook
from sse_starlette.sse import EventSourceResponse

# Lưu trữ các queue lắng nghe theo từng Job ID
# Key: job_id, Value: asyncio.Queue()
active_job_streams = {}

router = APIRouter(prefix='/bot', tags=["Bot Automation"])
queue = Queue(connection=redis_client)
UPLOAD_DIR = "./bot_media_tmp"

@router.get("/job-stream/{job_id}")
async def job_stream(request: Request, job_id: str):
    
    async def event_generator():
        # Đăng ký kênh Pub/Sub trước để tránh sót tin nhắn trong lúc check trạng thái
        pubsub = async_redis_client.pubsub()
        channel_name = f"job_channel:{job_id}"
        await pubsub.subscribe(channel_name)
        
        print(f"🔌 [SSE Connect] Trình duyệt đã kết nối vào luồng Job: {job_id}")
        
        # --- ✨ LOGIC KIỂM TRA TRẠNG THÁI HIỆN TẠI CỦA TÁC VỤ ---
        initial_status = "connected" 
        try:
            # Dùng redis_client đồng bộ để fetch thông tin Job từ RQ
            rq_job = Job.fetch(job_id, connection=redis_client)
            rq_status = rq_job.get_status() # Các trạng thái: 'queued', 'started', 'finished', 'failed'
            
            if rq_status == "started":
                # Nếu RQ báo 'started' nghĩa là Worker đang ôm Selenium chạy rồi!
                initial_status = "processing"
            elif rq_status == "finished":
                initial_status = "completed"
            elif rq_status == "failed":
                initial_status = "failed"
        except Exception as e:
            print(f"⚠️ Không thể check trạng thái RQ cho job {job_id}: {e}")

        # Gửi trạng thái thực tế này xuống Frontend ngay khi vừa kết nối xong
        yield dict(data=json.dumps({"status": initial_status}))
        
        # Nếu job đã xong hoặc lỗi từ trước, ngắt kết nối luôn không cần loop nữa
        if initial_status in ["completed", "failed"]:
            await pubsub.unsubscribe(channel_name)
            return

        # --- VÒNG LẶP HÓNG CÁC SỰ KIỆN TIẾP THEO ---
        try:
            while True:
                if await request.is_disconnected():
                    print(f"❌ [SSE Disconnect] Trình duyệt đã ngắt kết nối | Job: {job_id}")
                    break
                
                # Timeout thấp để vòng lặp xoay liên tục, check ngắt kết nối nhạy hơn
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
                
                if message:
                    raw_data = message['data']
                    data_str = raw_data.decode('utf-8') if isinstance(raw_data, bytes) else raw_data
                    status_data = json.loads(data_str)
                    
                    yield dict(data=json.dumps(status_data))
                    
                    if status_data.get("status") in ["completed", "failed"]:
                        break
                        
                await asyncio.sleep(0.2)
        finally:
            await pubsub.unsubscribe(channel_name)

    return EventSourceResponse(event_generator())

@router.post("/post-by-group-ids")
async def post_by_group_ids(
    uid: str = Form(...),
    username: str = Form(...),
    content: str = Form(""),
    group_ids: str = Form(...), # Nhận chuỗi "ALL" hoặc JSON string từ FormData
    images: List[UploadFile] = File(default=[]), # Nhận danh sách file ảnh từ uploader
    db: Session = Depends(get_db_session)
):
    print(group_ids)
    
    final_group_ids = []

    # 1. Xử lý rẽ nhánh mặc định ALL hoặc Chọn cụ thể
    if group_ids == "ALL":
        # Tự lôi từ DB ra giống hệt hàm get_group_ids có sẵn của bạn
        account = db.exec(select(SocialAccount).where(SocialAccount.uid == uid, SocialAccount.username == username)).first()
        if not account or not account.groups_data:
            raise HTTPException(status_code=404, detail="Không có dữ liệu nhóm để chạy mặc định ALL")
        
        final_group_ids = [
            g.get("group_id") if isinstance(g, dict) else getattr(g, "group_id", "")
            for g in account.groups_data
        ]
        final_group_ids = [gid for gid in final_group_ids if gid]
    else:
        try:
            # 1. Parse chuỗi JSON gửi từ Frontend lên (Kết quả ra list các dict)
            raw_groups = json.loads(group_ids)
            
            if not isinstance(raw_groups, list):
                raise HTTPException(status_code=400, detail="Cấu trúc group_ids phải là một mảng")
            
            # 2. CHUYỂN ĐỔI: Duyệt qua từng dict trong list để bốc riêng key 'group_id'
            final_group_ids = [
                item.get("group_id") if isinstance(item, dict) else str(item)
                for item in raw_groups
            ]
            
            # 3. Lọc bỏ các giá trị rỗng hoặc None nếu có lỗi dữ liệu từ client
            final_group_ids = [gid for gid in final_group_ids if gid]
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Định dạng group_ids JSON không hợp lệ")

    if not final_group_ids:
        raise HTTPException(status_code=400, detail="Mảng group_id xử lý cuối cùng trống rỗng!")

    # 2. Loại bỏ trùng lặp (Tối ưu)
    unique_ids = list(set(final_group_ids))

    # 3. Xử lý lưu ảnh xuống thư mục tạm nếu có images...
    session_data = get_user_session(uid)
    saved_paths = []
    
    if images:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        for img in images:
            if not img.filename:
                continue
            ext = os.path.splitext(img.filename)[1].lower()
            # Khử trùng lặp file bằng UUID
            filename = f"task_{uid}_{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            # Ghi file bất đồng bộ (Non-blocking I/O)
            content_binary = await img.read()
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content_binary)
                
            saved_paths.append(os.path.abspath(file_path))

    task_data = {
        "uid": uid,
        "cookie_json": session_data.get("cookies", []),
        "user_agent": session_data.get("user_agent", ""),
        "group_ids": unique_ids,
        "content": content,
        "image_paths": saved_paths  
    }

    # 4. Đẩy sang cho RQ Worker chạy ngầm (Truyền thêm content và danh sách ảnh vào bọc Selenium)
    job = queue.enqueue(run_selenium_task, task_data, job_timeout=-1)

    print(f"🚀 Đã đẩy {len(unique_ids)} ID nhóm kèm bài viết '{content}' và {len(images)} ảnh xuống Worker")

    return {"status": "queued", "job_id": job.id, "images_received": len(saved_paths)}

@router.post("/scan-group")
async def scan_group(uid: str = Form(...), username: str = Form(...)):
    # 1. Lấy danh sách các Job đang chạy trong hàng đợi
    registry = StartedJobRegistry(queue=queue)
    running_job_ids = registry.get_job_ids()
    waiting_job_ids = queue.get_job_ids()
    
    all_active_job_ids = running_job_ids + waiting_job_ids

    # 2. Kiểm tra xem có Job nào trùng UID đang chạy không
    for j_id in all_active_job_ids:
        try:
            active_job = Job.fetch(j_id, connection=redis_client)
            # active_job.args[0] chính là tham số 'uid' được truyền vào hàm target_scan_group_function
            if active_job.args and active_job.args[0] == uid:
                raise HTTPException(status_code=400, detail="Tài khoản này đang được bot quét rồi, vui lòng đợi xong!")
        except:
            continue

    session_data = get_user_session(uid)

    task_data = {
        "username": username,
        "uid": uid,
        "cookie_json": session_data.get("cookies", []),
        "user_agent": session_data.get("user_agent", ""),
    }

    job = queue.enqueue(run_selenium_scan_group, task_data)
    print(job.get_status())
    return {"status": "queued", "job_id": job.id}
    
@router.post("/ping", dependencies=[Depends(verify_odoo_hook)])
async def ping_odoo(payload, db: Session = Depends(get_db_session)):
    print(payload)
    return {"status": "success"}