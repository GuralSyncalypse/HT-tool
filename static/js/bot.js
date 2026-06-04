const runBotBtn = document.getElementById("btn-run-bot");
const imageInput = document.getElementById("imageInput");
const imagePreviewContainer = document.getElementById("imagePreviewContainer");
const startBtn = document.getElementById("btn-start")
const botStatus = document.getElementById("bot-status");
const selectUid = document.getElementById("select-uid");

export function initBotButton() {

    runBotBtn.addEventListener("click", async () => {

        const selectedUid = selectUid.value;

        if (!selectedUid) {
            botStatus.innerText =
                "⚠️ Vui lòng chọn một tài khoản hợp lệ!";
            return;
        }

        runBotBtn.disabled = true;
        runBotBtn.innerText = "⏳ Đang gửi yêu cầu...";

        try {

            const response = await fetch("/run-bot", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    uid: selectedUid
                })
            });

            const data = await response.json();

            if (response.ok) {
                botStatus.innerText =
                    `✅ Job ID: ${data.job_id}`;
            } else {
                botStatus.innerText =
                    `❌ ${data.message}`;
            }

        } catch (error) {

            console.error(error);

            botStatus.innerText =
                "❌ Không thể kết nối Server.";

        } finally {

            runBotBtn.disabled = false;
            runBotBtn.innerText =
                "🚀 Chạy Bot Selenium";
        }
    });
}


// Bắt sự kiện khi người dùng nhấn nút gửi
startBtn.addEventListener("click", async () => {
    
    // 1. Tìm các phần tử DOM
    const textarea = document.querySelector("textarea");
    const imageInput = document.getElementById("imageInput");
    const imagePreviewContainer = document.getElementById("imagePreviewContainer"); // Thêm dòng này để xóa ảnh preview
    const statusEl = document.getElementById("status"); 

    const textContent = textarea.value.trim();
    const files = imageInput.files;

    // Kiểm tra dữ liệu trống
    if (!textContent && files.length === 0) {
        alert("Vui lòng nhập nội dung hoặc chọn ít nhất 1 hình ảnh!");
        return;
    }

    // 2. Tạo đối tượng FormData
    const formData = new FormData();
    formData.append("uid", selectUid.value); // UID của tài khoản FB đang chạy
    formData.append("action", "auto_post_feed"); // Hành động muốn bot thực hiện
    formData.append("content", textContent);     // Nội dung văn bản

    // Duyệt qua danh sách file và đẩy vào mảng "images"
    if (files && files.length > 0) {
        for (let i = 0; i < files.length; i++) {
            formData.append("images", files[i]);
        }
    }

    try {
        if (statusEl) statusEl.innerText = "Đang gửi dữ liệu...";
        
        // Vô hiệu hóa nút tạm thời để tránh người dùng click liên tục (Double submit)
        startBtn.disabled = true;

        // 3. Gửi sang FastAPI
        const response = await fetch("http://127.0.0.1:8000/run-bot", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            if (statusEl) statusEl.innerText = "Đã thêm vào hàng đợi!";
            alert("Gửi lệnh cho bot thành công!");
            
            // --- TIẾN HÀNH RESET FORM SAU KHI THÀNH CÔNG ---
            textarea.value = "";
            imageInput.value = ""; // Xóa sạch các file đã nạp trong ô input ẩn
            if (imagePreviewContainer) {
                imagePreviewContainer.innerHTML = ""; // Xóa sạch các ảnh hiển thị xem trước
            }
        } else {
            if (statusEl) statusEl.innerText = "Lỗi hệ thống";
            // Dự phòng trường hợp lỗi 500 không có trường .detail
            const errorMsg = result && result.detail ? result.detail : "Lỗi không xác định từ Server.";
            alert("Thất bại: " + errorMsg);
        }
    } catch (error) {
        console.error("Lỗi kết nối server:", error);
        if (statusEl) statusEl.innerText = "Lỗi kết nối";
        alert("Không thể kết nối tới server API. Hãy chắc chắn FastAPI đang chạy!");
    } finally {
        // Mở lại nút bấm dù thành công hay thất bại
        startBtn.disabled = false;
    }
});