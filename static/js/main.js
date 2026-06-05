// main.js
import { loadActiveAccounts, loadGroups } from "./groups.js";
import { initImageUploader } from "./imageUploader.js"; 
import { initPostButton, initUpdateGroupButton } from "./bot.js"; 

// ==========================================
// 1. KIỂM TRA QUYỀN TRUY CẬP NGAY LẬP TỨC
// ==========================================
// Kiểm tra xem token nằm ở kho lưu trữ nào
const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');

if (!token) {
    // Nếu không tìm thấy token ở cả 2 nơi, bắt quay về login
    window.location.href = '/login';
}

// Hàm bổ trợ để gọi API có đính kèm Token (Dùng thay cho fetch thông thường nếu cần)
export async function fetchWithAuth(url, options = {}) {
    const currentToken = localStorage.getItem('access_token');
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${currentToken}`
    };
    const response = await fetch(url, options);
    if (response.status === 401) {
        localStorage.removeItem('access_token');
        window.location.href = "/login";
    }
    return response;
}

// ==========================================
// 2. KHỞI TẠO LOGIC KHI DOM ĐÃ SẴN SÀNG
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    // --- XỬ LÝ ĐĂNG NHẬP / ĐĂNG XUẤT TRÊN UI ---
    const guestZone = document.getElementById('auth-guest-zone');
    const userZone = document.getElementById('auth-user-zone');
    const logoutBtn = document.getElementById('btn-logout-ui');

    if (token) {
        // Đã có token: Hiện vùng thông tin user, ẩn vùng nút đăng nhập khách
        if (guestZone) guestZone.classList.add('hidden');
        if (userZone) userZone.classList.remove('hidden');
        
        // Lấy thông tin Username từ Backend để hiển thị lên màn hình
        fetch('/users/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => {
            if (res.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = "/login";
            }
            return res.json();
        })
        .then(data => {
            const nameDisplay = document.getElementById('user-display-name');
            if (nameDisplay && data.username) {
                nameDisplay.innerText = data.username;
            }
        })
        .catch(err => console.error("Lỗi lấy thông tin user:", err));
    }

    // Xử lý sự kiện khi bấm nút Đăng xuất
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                // Gọi API logout để FastAPI đẩy token này vào blacklist của Redis
                await fetch('/logout', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` }
                });
            } catch (err) {
                console.error("Lỗi gọi API logout:", err);
            } finally {
                // Cho dù API có lỗi hay không thì vẫn xóa sạch token ở Client và về trang login
                localStorage.removeItem('access_token');
                window.location.href = "/login";
            }
        });
    }

    const uid = document.getElementById("select-uid").value;

    // Lấy username từ phần tử hiển thị trên UI giống như lúc làm nút Update
    const usernameElement = document.getElementById('user-display-name');
    const username = usernameElement ? usernameElement.innerText.trim() : "";

    // Truyền cả UID và Username vào hàm tải nhóm
    loadGroups(username, uid);

    // --- LOGIC GỐC CỦA BẠN GIỮ NGUYÊN ---
    loadActiveAccounts();

    // 1. Khởi tạo uploader
    initImageUploader();

    initUpdateGroupButton();

    // 2. Khởi tạo logic nút gửi bài
    initPostButton(); 

    document.getElementById("select-uid").addEventListener("change", (e) => {
        const uid = e.target.value;

        // Lấy username từ phần tử hiển thị trên UI giống như lúc làm nút Update
        const usernameElement = document.getElementById('user-display-name');
        const username = usernameElement ? usernameElement.innerText.trim() : "";

        // Truyền cả UID và Username vào hàm tải nhóm
        loadGroups(username, uid);
    });
});