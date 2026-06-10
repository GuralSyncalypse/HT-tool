const imageInput = document.getElementById("imageInput");
const imagePreviewContainer = document.getElementById("imagePreviewContainer");
const startBtn = document.getElementById("btn-start")
const botStatus = document.getElementById("bot-status");
const selectUid = document.getElementById("select-uid");


// export function initBotButton() {

//     runBotBtn.addEventListener("click", async () => {

//         const selectedUid = selectUid.value;

//         if (!selectedUid) {
//             botStatus.innerText =
//                 "⚠️ Vui lòng chọn một tài khoản hợp lệ!";
//             return;
//         }

//         runBotBtn.disabled = true;
//         runBotBtn.innerText = "⏳ Đang gửi yêu cầu...";

//         try {

//             const response = await fetch("/run-bot", {
//                 method: "POST",
//                 headers: {
//                     "Content-Type": "application/json"
//                 },
//                 body: JSON.stringify({
//                     uid: selectedUid
//                 })
//             });

//             const data = await response.json();

//             if (response.ok) {
//                 botStatus.innerText =
//                     `✅ Job ID: ${data.job_id}`;
//             } else {
//                 botStatus.innerText =
//                     `❌ ${data.message}`;
//             }

//         } catch (error) {

//             console.error(error);

//             botStatus.innerText =
//                 "❌ Không thể kết nối Server.";

//         } finally {

//             runBotBtn.disabled = false;
//             runBotBtn.innerText =
//                 "🚀 Chạy Bot Selenium";
//         }
//     });
// }

// Hàm phụ: Tự động chạy ngầm đi hỏi thăm trạng thái của Job ID
async function checkJobStatus(jobId) {
    try {
        const response = await fetch(`/api/v1/bot/check-job/${jobId}`);
        if (!response.ok) return "failed";
        const result = await response.json();
        return result.status;
    } catch (error) {
        console.error("Lỗi kết nối check job:", error);
        return "failed";
    }
}

// Hàm phụ trách chạy vòng lặp Polling (Tách riêng ra để tái sử dụng)
async function startPolling(btnUpdate, originalText, jobId, taskName) {
    let isDone = false;
    
    // Bật hiệu ứng quay và khóa nút
    btnUpdate.disabled = true;
    btnUpdate.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Đang xử lý ngầm...`;

    while (!isDone) {
        await new Promise(resolve => setTimeout(resolve, 2000)); 
        const status = await checkJobStatus(jobId);
        
        if (status === "completed") {
            alert("Bot đã quét và cập nhật nhóm thành công! 🎉");
            isDone = true;
            localStorage.removeItem(taskName); // Xóa ID khi xong
        } else if (status === "failed") {
            alert("Tác vụ quét nhóm ngầm bị lỗi hoặc đã thất bại! ❌");
            isDone = true;
            localStorage.removeItem(taskName); // Xóa ID khi lỗi
        }
        // Nếu "pending" hoặc "processing", vòng lặp tiếp tục chạy...
    }

    // Tắt hiệu ứng quay, trả nút về ban đầu
    btnUpdate.disabled = false;
    btnUpdate.innerHTML = originalText;
}

export function initUpdateGroupButton() {
    const btnUpdate = document.getElementById("btn-update-group");
    if (!btnUpdate) return; 

    const originalText = btnUpdate.innerHTML;

    // 🌟 LOGIC QUAN TRỌNG: Kiểm tra ngay khi vừa load/reset lại trang
    const taskName = "current_scan_job_id"
    const savedJobId = localStorage.getItem(taskName);
    if (savedJobId) {
        // Nếu tìm thấy job_id cũ chưa chạy xong, tự động kích hoạt lại vòng lặp quay nút
        startPolling(btnUpdate, originalText, savedJobId, taskName);
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
            // Tạm thời khóa nút nhanh để tránh double click
            btnUpdate.disabled = true;
            btnUpdate.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Đang khởi tạo...`;

            const response = await fetch("/api/v1/bot/scan-group", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.job_id) {
                // 🌟 Lưu job_id vào bộ nhớ trình duyệt trước khi chạy Polling
                localStorage.setItem(taskName, result.job_id);
                
                // Kích hoạt vòng lặp chờ backend
                await startPolling(btnUpdate, originalText, result.job_id, taskName);
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
        console.log(`Phát hiện tiến trình cũ chưa xong (#${savedJobId}). Đang khôi phục Polling...`);
        // Tự động chạy lại vòng lặp quản lý nút bấm
        startPolling(btnPost, originalText, savedJobId, taskName);
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

                // 🌟 Lưu động job_id vào bộ nhớ với taskName tương ứng
                localStorage.setItem(taskName, jobId);
                
                // Kích hoạt vòng lặp chờ backend xử lý (Hàm này sẽ chịu trách nhiệm unlock nút khi xong)
                await startPolling(btnPost, originalText, jobId, taskName);

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


// export async function sendGroupsToBackend() {
//     // 1. Kiểm tra xem bộ nhớ allGroups toàn cục có dữ liệu hay không
//     if (!allGroups || allGroups.length === 0) {
//         alert("Hiện tại chưa có dữ liệu nhóm nào được tải về UI!");
//         return;
//     }

//     // 2. Vét sạch TOÀN BỘ group_id của tất cả các trang đã lưu trong allGroups
//     const wholeGroupIds = allGroups.map(group => group.group_id);

//     console.log(`🎯 Đã thu thập tổng cộng ${wholeGroupIds.length} ID từ tất cả các trang:`, wholeGroupIds);

//     try {
//         // 3. Gọi fetchWithAuth và truyền THẲNG mảng vào body (không bọc qua payload object)
//         const response = await fetchWithAuth("/api/v1/bot/post-by-group-ids", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json"
//             },
//             body: JSON.stringify(wholeGroupIds) // <-- Gửi trực tiếp mảng ["id1", "id2", ...]
//         });

//         if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

//         const result = await response.json();
//         alert(`Thành công! Đã gửi toàn bộ ${wholeGroupIds.length} nhóm xuống Backend để chạy Selenium.`);
//         console.log("Kết quả nhận được từ server:", result);

//     } catch (error) {
//         console.error("Lỗi khi gửi danh sách tổng xuống backend:", error);
//         alert("Gửi dữ liệu thất bại. Hãy kiểm tra lại kết nối mạng hoặc log của server.");
//     }
// }