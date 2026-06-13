const imageInput = document.getElementById("imageInput");
const imagePreviewContainer = document.getElementById("imagePreviewContainer");
const startBtn = document.getElementById("btn-start");
const botStatus = document.getElementById("bot-status");
const selectUid = document.getElementById("select-uid");

// 🚀 HÀM MỚI: Quản lý trạng thái bằng Server-Sent Events (Thay thế hoàn toàn cơ chế Polling cũ)
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
            console.log("Trạng thái nhận được từ SSE:", data.status);

            if (data.status === "connected") {
                // Trường hợp tác vụ vẫn đang nằm trong hàng đợi (chưa tới lượt worker bốc)
                btnUpdate.disabled = true;
                btnUpdate.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Tác vụ đang xếp hàng...`;
            } 
            else if (data.status === "processing") {
                // Khi F5 xong mà Backend bảo job này đang chạy dở, nút sẽ lập tức quay icon spider quét nhóm ngay!
                btnUpdate.disabled = true;
                btnUpdate.innerHTML = `<i class="fas fa-spider fa-spin"></i> Bot đang quét nhóm...`;
            } 
            else if (data.status === "completed") {
                alert("Bot đã quét và cập nhật nhóm thành công! 🎉");
                totalCleanup(); 
            } 
            else if (data.status === "failed") {
                let errorMsg = "Tác vụ quét nhóm ngầm bị lỗi hoặc đã thất bại! ❌";
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

export function initUpdateGroupButton() {
    const btnUpdate = document.getElementById("btn-update-group");
    if (!btnUpdate) return; 

    const originalText = btnUpdate.innerHTML;
    const taskName = "current_scan_job_id";

    // 🌟 LOGIC KHI TẢI LẠI TRANG: Nếu trang bị F5, tự động thiết lập lại ống nghe SSE dựa trên ID cũ
    const savedJobId = localStorage.getItem(taskName);
    if (savedJobId) {
        startSSENotifier(btnUpdate, originalText, savedJobId, taskName);
    }

    btnUpdate.addEventListener("click", async function() {
        const selectUidElement = document.getElementById("select-uid");
        if (!selectUidElement) { alert("Không tìm thấy UID trên UI!"); return; }

        const uid = selectUidElement.value; 
        if (!uid) { alert("Không tìm thấy UID cần cập nhật!"); return; }

        const usernameElement = document.getElementById("user-display-name");
        const username = usernameElement ? usernameElement.innerText.trim() : "";

        const formData = new FormData();
        formData.append("uid", uid);
        formData.append("username", username);

        try {
            // Khóa nhanh nút chặn double-click
            btnUpdate.disabled = true;
            btnUpdate.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Đang khởi tạo...`;

            const response = await fetch("/api/v1/bot/scan-group", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.job_id) {
                // Lưu ID vào localStorage phòng trường hợp F5
                localStorage.setItem(taskName, result.job_id);
                
                // Kích hoạt bộ nghe thời gian thực SSE
                startSSENotifier(btnUpdate, originalText, result.job_id, taskName);
            } else {
                alert(`Lỗi: ${result.detail || "Không thể chạy bot"}`);
                btnUpdate.disabled = false;
                btnUpdate.innerHTML = originalText;
            }
        } catch (error) {
            console.error("Lỗi kết nối:", error);
            alert("Không thể kết nối tới Server API!");
            btnUpdate.disabled = false;
            btnUpdate.innerHTML = originalText;
        }
    });
}

// bot.js
import { getSelectedFiles, resetUploader } from "./imageUploader.js";
import { selectedGroups } from "./groups.js";
import { fetchWithAuth } from "./main.js";

export function initPostButton() {
    const btnPost = document.getElementById("btn-start");
    const taskName = "current_post_job_id";

    if (!btnPost) return;

    const originalText = btnPost.innerHTML;

    // --- KHÔI PHỤC ĐỘNG KHI F5 / TRANH CHẤP TRANG ---
    const savedJobId = localStorage.getItem(taskName);
    if (savedJobId) {
        startSSENotifier(btnPost, originalText, savedJobId, taskName);
    }

    btnPost.addEventListener("click", async () => {
        const uid = document.getElementById("select-uid")?.value;
        const usernameElement = document.getElementById("user-display-name"); 
        const username = usernameElement ? usernameElement.innerText.trim() : "";
        const content = document.getElementById("content-box")?.value || "";
        const selectedFiles = typeof getSelectedFiles === "function" ? getSelectedFiles() : []; 

        // Kiểm tra điều kiện đầu vào
        if (!uid || !username) { 
            alert("Vui lòng chọn tài khoản hợp lệ!"); 
            return; 
        }

        if (content === '') {
            alert("Vui lòng nhập nội dung!");
            return;
        }   

        // Chuẩn bị dữ liệu Form
        const formData = new FormData();
        formData.append("uid", uid);
        formData.append("username", username);
        formData.append("content", content);

        // Giả định biến selectedGroups tồn tại ở phạm vi ngoài (global/module scope)
        if (typeof selectedGroups === "undefined" || selectedGroups.length === 0) {
            formData.append("group_ids", "ALL");
        } else {
            formData.append("group_ids", JSON.stringify(selectedGroups));
        }

        selectedFiles.forEach((file) => { formData.append("images", file); });

        try {
            // --- BƯỚC 2: GỬI LỆNH TẠO JOB ĐĂNG BÀI ---
            const response = await fetch("/api/v1/bot/post-by-group-ids", {
                method: "POST",
                body: formData 
            });

            const result = await response.json();

            if (response.ok && result.job_id) {
                const jobId = result.job_id;

                // Lưu ID vào localStorage phòng trường hợp F5
                localStorage.setItem(taskName, jobId);
                
                // Kích hoạt bộ nghe thời gian thực SSE
                startSSENotifier(btnPost, originalText, jobId, taskName);

            } else {
                alert(`Gửi bài thất bại: ${result.detail || "Vui lòng kiểm tra cấu hình hoặc bot không thể chạy."}`);
                // Khôi phục nút nếu API trả lỗi cấu hình đầu vào công việc
                btnPost.disabled = false;
                btnPost.innerHTML = originalText;
            }
        } 
        catch (error) {
            console.error("Lỗi kết nối API khởi tạo:", error);
            alert("Không thể kết nối tới Server API!");
            // Khôi phục nút nếu lỗi mạng không gửi được lệnh tạo Job
            btnPost.disabled = false;
            btnPost.innerHTML = originalText;
        }
    });
}
