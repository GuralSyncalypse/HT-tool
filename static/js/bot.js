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
            const response = await fetch("http://localhost:8000/bot/scan-group", {
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

export function initPostButton() {
    const btnPost = document.getElementById("btn-start"); // ID nút gửi bài của bạn

    if (!btnPost) return;

    btnPost.addEventListener("click", async () => {
        // 1. Lấy dữ liệu từ giao diện
        const uid = document.getElementById("select-uid")?.value;
        const action = "POST"; // Hoặc lấy từ input/dropdown của bạn
        const content = document.getElementById("content-box")?.value || "";
        
        // 2. Lấy danh sách file ảnh từ module uploader
        const selectedFiles = getSelectedFiles(); 

        if (!uid || !action) {
            alert("Vui lòng điền đầy đủ thông tin UID và Action!");
            return;
        }

        // 3. Khởi tạo FormData
        const formData = new FormData();
        formData.append("uid", uid);
        formData.append("action", action);
        formData.append("content", content);

        // 4. QUAN TRỌNG: Loop qua mảng file và append chung vào 1 key 'images'
        selectedFiles.forEach((file) => {
            formData.append("images", file); 
        });

        try {
            btnPost.disabled = true;
            btnPost.innerText = "Đang gửi...";

            // 5. Gửi request lên FastAPI
            const response = await fetch("/run-bot", {
                method: "POST",
                body: formData 
                // LƯU Ý: KHÔNG set Header 'Content-Type'. 
                // Trình duyệt sẽ tự định nghĩa Content-Type là multipart/form-data kèm boundary chuẩn xác.
            });

            if (response.ok) {
                const result = await response.json();
                alert("Gửi bài thành công!");
                
                // 6. Reset uploader sau khi gửi thành công để giải phóng bộ nhớ
                const btnSelectImage = document.getElementById('btnSelectImage');
                const imagePreviewContainer = document.getElementById('imagePreviewContainer');
                resetUploader(btnSelectImage, imagePreviewContainer);
                if (document.getElementById("contentInput")) {
                    document.getElementById("contentInput").value = "";
                }
            } else {
                const errorData = await response.json();
                console.error("Lỗi từ server:", errorData);
                alert("Có lỗi xảy ra khi gửi bài!");
            }
        } catch (error) {
            console.error("Lỗi kết nối:", error);
            alert("Không thể kết nối tới server!");
        } finally {
            btnPost.disabled = false;
            btnPost.innerText = "Đăng bài";
        }
    });
}