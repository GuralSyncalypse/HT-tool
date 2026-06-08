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

export function initUpdateGroupButton() {
    const btnUpdate = document.getElementById("btn-update-group");
    
    // Kiểm tra xem nút có tồn tại trên giao diện không trước khi gán sự kiện
    if (!btnUpdate) return; 

    btnUpdate.addEventListener("click", async function() {
        // 1. Lấy đúng phần tử select-uid từ DOM
        const selectUidElement = document.getElementById("select-uid");
        if (!selectUidElement) {
            alert("Không tìm thấy phần tử chọn UID trên giao diện!");
            return;
        }

        const uid = selectUidElement.value; 

        if (!uid) {
            alert("Không tìm thấy UID cần cập nhật!");
            return;
        }

        const usernameElement = document.getElementById("user-display-name");
        const username = usernameElement ? usernameElement.innerText.trim() : "";

        // 2. Tạo FormData để gửi lên API dạng Form(...)
        const formData = new FormData();
        formData.append("uid", uid);
        formData.append("username", username)

        try {
            // Thay đổi URL cho đúng với domain/port của project bạn
            const response = await fetch("/api/v1/bot/scan-group", {
                method: "POST",
                body: formData // Không cần set Headers "Content-Type"
            });

            const result = await response.json();

            if (response.ok) {
                alert(`Đã thêm tác vụ cập nhật vào hàng đợi! Job ID: ${result.job_id}`);
            } else {
                alert(`Lỗi: ${result.detail || "Không thể chạy bot"}`);
            }
        } catch (error) {
            console.error("Lỗi kết nối:", error);
            alert("Không thể kết nối tới Server API!");
        }
    });
}

// bot.js
import { getSelectedFiles, resetUploader } from "./imageUploader.js";
import { selectedGroups } from "./groups.js";
import { fetchWithAuth } from "./main.js";

export function initPostButton() {
    const btnPost = document.getElementById("btn-start");
    if (!btnPost) return;

    btnPost.addEventListener("click", async () => {
        const uid = document.getElementById("select-uid")?.value;
        // Lấy thêm username hiển thị trên UI để làm căn cứ khớp query cho Backend
        const usernameElement = document.getElementById("user-display-name"); 
        const username = usernameElement ? usernameElement.innerText.trim() : "";
        const content = document.getElementById("content-box")?.value || "";
        const selectedFiles = getSelectedFiles(); 

        if (!uid || !username) { alert("Vui lòng chọn tài khoản hợp lệ!"); return; }


        if (content == '') {
            alert("Vui lòng nhập nội dung!");
            return;
        }   

        // 2. Khởi tạo FormData
        const formData = new FormData();
        formData.append("uid", uid);
        formData.append("username", username);
        formData.append("content", content);

        // 🌟 3. LOGIC QUAN TRỌNG: Mặc định gửi "ALL", có chọn thì gửi mảng string JSON
        if (selectedGroups.length === 0) {
            formData.append("group_ids", "ALL");
        } else {
            formData.append("group_ids", JSON.stringify(selectedGroups));
        }

        // Đính kèm danh sách file ảnh
        selectedFiles.forEach((file) => { formData.append("images", file); });

        try {
            btnPost.disabled = true;
            btnPost.innerText = "Đang gửi...";

            const response = await fetch("/api/v1/bot/post-by-group-ids", {
                method: "POST",
                body: formData // Trình duyệt tự sinh multipart/form-data
            });

            if (response.ok) {
                alert("Đã gửi tác vụ đăng bài lên Server thành công!");
                // Clear nội dung content-box và ảnh preview tại đây...
                document.getElementById("content-box").value = ''
                resetUploader(btnPost, imagePreviewContainer)
            } else {
                alert("Gửi bài thất bại, vui lòng kiểm tra cấu hình.");
            }
        } catch (error) {
            console.error("Lỗi kết nối:", error);
        } finally {
            btnPost.disabled = false;
            btnPost.innerText = "Đăng bài";
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