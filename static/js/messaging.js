// messaging.js
import { checkAuthOrRedirect, fetchWithAuth, handleLogout } from "./auth.js"; 
import { loadActiveAccounts } from "./groups.js";

function startSSENotifier(btnUpdate, originalText, jobId, taskName) {
    const eventSource = new EventSource(`/api/v1/bot/job-stream/${jobId}`);

    // ✨ HÀM DỌN DẸP HOÀN TOÀN (Chỉ gọi khi JOB ĐÃ XONG hẳn)
    function totalCleanup() {
        eventSource.close();
        localStorage.removeItem(taskName); // 🌟 Xóa ID khỏi máy CHỈ khi xong hoặc lỗi nặng
        if (btnUpdate) {
            btnUpdate.disabled = false;
            btnUpdate.innerHTML = originalText;
        }
    }

    // ✨ HÀM DỌN DẸP TẠM THỜI (Khi User chủ động F5)
    function temporaryCleanup() {
        eventSource.close(); // Chỉ đóng ống nghe SSE của trang cũ, GIỮ NGUYÊN localStorage
    }

    eventSource.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);
            console.log(data)
            const message = `Gửi (${data.successCount}    thành công)`;
            console.log("Trạng thái nhận được từ SSE:", data.status);

            if (data.status === "connected") {
                btnUpdate.disabled = true;
                btnUpdate.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Tác vụ đang xếp hàng...`;
            } 
            else if (data.status === "processing") {
                btnUpdate.disabled = true;
                btnUpdate.innerHTML = `<i class="fas fa-spider fa-spin"></i> Bot đang bắn SMS...`;
            } 
            else if (data.status === "completed") {
                alert(message);
                totalCleanup(); 
            } 
            else if (data.status === "failed") {
                let errorMsg = "Tác vụ bị lỗi hoặc đã thất bại! ❌";
                if (data.reason === "auth_failed") errorMsg = "Đăng nhập thất bại! Kiểm tra Cookie. ❌";
                else if (data.error) errorMsg = `Lỗi hệ thống: ${data.error} ❌`;
                
                alert(errorMsg);
                totalCleanup(); 
            }
        } catch (error) {
            console.error("Lỗi parse dữ liệu SSE:", error);
            totalCleanup();
        }
    };

    eventSource.onerror = function (err) {
        console.error("Lỗi kết nối đường truyền SSE:", err);
        
        // 🌟 XỬ LÝ KHI USER F5:
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log("User chủ động F5, giữ nguyên Job ID trong localStorage để trang sau kết nối lại.");
            temporaryCleanup(); // Chỉ đóng kết nối, không xóa localStorage
            return;
        }

        // Nếu mất kết nối thật (rớt mạng, sập server) chứ không phải do F5
        alert("Đường truyền kết nối với Bot bị ngắt quãng! ⚠️");
        totalCleanup();
    };
}

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Chặn luôn tại cửa sổ này nếu user chưa login
    const token = checkAuthOrRedirect();
    if (!token) return; 

    // Gắn sự kiện nút logout của trang này nếu có
    const logoutBtn = document.getElementById('btn-logout-ui');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    // 2. Viết tiếp các logic tải tin nhắn, chat chit tại đây...
    // --- KHAI BÁO CÁC PHẦN TỬ UI ---
    const guestZone = document.getElementById('auth-guest-zone');
    const userZone = document.getElementById('auth-user-zone');
    const uidSelect = document.getElementById("select-uid");
    const nameDisplay = document.getElementById('user-display-name');

    let authenticatedUsername = "";

    // Hiển thị UI User vùng đăng nhập
    if (guestZone) guestZone.classList.add('hidden');
    if (userZone) userZone.classList.remove('hidden');
    
    // Gọi API lấy thông tin user công khai
    try {
        const res = await fetchWithAuth('/api/v1/users/me');
        const data = await res.json();
        if (data && data.username) {
            authenticatedUsername = data.username;
            if (nameDisplay) nameDisplay.innerText = data.username;
        }
    } catch (err) {
        console.error("Lỗi lấy thông tin user từ API:", err);
    }

    await loadActiveAccounts(); 
    const uid = uidSelect ? uidSelect.value : "";

    initSendBtn()
});

export function initSendBtn() {
    const startBtn = document.getElementById("btn-start");
    const taskName = "current_send_job_id";

    if (!startBtn) return;

    const originalText = startBtn.innerHTML;

    // --- KHÔI PHỤC ĐỘNG KHI F5 / TRANH CHẤP TRANG ---
    const savedJobId = localStorage.getItem(taskName);
    if (savedJobId) {
        startSSENotifier(startBtn, originalText, savedJobId, taskName);
    }

    startBtn.addEventListener("click", async () => {
        const uid = document.getElementById("select-uid")?.value;
        const usernameElement = document.getElementById("user-display-name"); 
        const username = usernameElement ? usernameElement.innerText.trim() : "";
        const content = document.getElementById("message-input")?.value || "";

        // ==========================================
        // LẤY DANH SÁCH UID TỪ BẢNG HTML
        // ==========================================
        const uidList = [];
        const tableRows = document.querySelectorAll("#uid-table-body tr");
        
        tableRows.forEach(row => {
            // Lấy cột thứ 2 (chứa UID)
            const uidCell = row.cells[1]; 
            if (uidCell) {
                const uidValue = uidCell.innerText.trim();
                // Loại bỏ trường hợp dòng thông báo trống "Vui lòng bấm nút..."
                if (uidValue && !uidValue.includes("Vui lòng")) {
                    uidList.push(uidValue);
                }
            }
        });

        // --- KIỂM TRA ĐIỀU KIỆN ĐẦU VÀO ---
        if (!uid || !username) { 
            alert("Vui lòng chọn tài khoản hợp lệ!"); 
            return; 
        }

        if (uidList.length === 0) {
            alert("Danh sách UID mục tiêu trống! Vui lòng tải file UID lên trước.");
            return;
        }

        if (content === '') {
            alert("Vui lòng nhập nội dung!");
            return;
        }   

        // Vô hiệu hóa nút bấm để tránh double-click
        startBtn.disabled = true;
        startBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Đang khởi tạo...`;

        // --- CHUẨN BỊ DỮ LIỆU FORM ---
        const formData = new FormData();
        formData.append("uid", uid);
        formData.append("username", username);
        // Chuyển mảng UID thành chuỗi JSON để truyền qua FormData an toàn
        formData.append("uid_list", JSON.stringify(uidList)); 
        formData.append("content", content);

        try {
            // --- BƯỚC 2: GỬI LỆNH TẠO JOB ĐĂNG BÀI ---
            const response = await fetch("/api/v1/bot/send-by-uids", {
                method: "POST",
                body: formData 
            });

            const result = await response.json();
            if (response.ok && result.job_id) {
                const jobId = result.job_id;
                const successCount = result.success_count;
                
                console.log(result);
                // Lưu ID vào localStorage phòng trường hợp F5
                localStorage.setItem(taskName, jobId);
                
                // Kích hoạt bộ nghe thời gian thực SSE
                startSSENotifier(startBtn, originalText, jobId, taskName);

            } else {
                alert(`Gửi bài thất bại: ${result.detail || "Vui lòng kiểm tra cấu hình hoặc bot không thể chạy."}`);
                startBtn.disabled = false;
                startBtn.innerHTML = originalText;
            }
        } 
        catch (error) {
            console.error("Lỗi kết nối API khởi tạo:", error);
            alert("Không thể kết nối tới Server API!");
            startBtn.disabled = false;
            startBtn.innerHTML = originalText;
        }
    });
}