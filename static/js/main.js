// main.js
import { loadActiveAccounts, loadGroups } from "./groups.js";
import { initImageUploader } from "./imageUploader.js"; 
import { initPostButton, initUpdateGroupButton } from "./bot.js"; 

// ==========================================
// 1. KIỂM TRA QUYỀN TRUY CẬP NGAY LẬP TỨC
// ==========================================
const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');

if (!token) {
    window.location.href = '/login';
}

/**
 * Hàm bổ trợ để gọi API có đính kèm Token
 */
export async function fetchWithAuth(url, options = {}) {
    const currentToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${currentToken}`
    };
    const response = await fetch(url, options);
    if (response.status === 401) {
        localStorage.removeItem('access_token');
        sessionStorage.removeItem('access_token');
        window.location.href = "/login";
    }
    return response;
}

// ==========================================
// 2. KHỞI TẠO LOGIC KHI DOM ĐÃ SẴN SÀNG
// ==========================================
document.addEventListener("DOMContentLoaded", async () => {
    // --- KHAI BÁO CÁC PHẦN TỬ UI ---
    const guestZone = document.getElementById('auth-guest-zone');
    const userZone = document.getElementById('auth-user-zone');
    const logoutBtn = document.getElementById('btn-logout-ui');
    const uidSelect = document.getElementById("select-uid");
    const nameDisplay = document.getElementById('user-display-name');

    // Biến lưu trữ username chuẩn lấy từ API
    let authenticatedUsername = "";

    // ---------------------------------------------------------
    // BƯỚC 1: Gọi API lấy Username chuẩn trước khi chạy App Logic
    // ---------------------------------------------------------
    if (token) {
        if (guestZone) guestZone.classList.add('hidden');
        if (userZone) userZone.classList.remove('hidden');
        
        try {
            const res = await fetchWithAuth('/api/v1/users/me');
            const data = await res.json();
            
            if (data && data.username) {
                authenticatedUsername = data.username; // Lấy trực tiếp dữ liệu từ API sạch
                if (nameDisplay) {
                    nameDisplay.innerText = data.username; // Chỉ ghi ra UI để hiển thị cho đẹp
                }
            }
        } catch (err) {
            console.error("Lỗi lấy thông tin user từ API:", err);
            authenticatedUsername = ""; 
        }
    }

    // ---------------------------------------------------------
    // BƯỚC 2: Khởi chạy Logic App (Sau khi chắc chắn bước 1 đã xong)
    // ---------------------------------------------------------
    // 1. Tải danh sách tài khoản active (Đổ UID vào dropdown)
    await loadActiveAccounts(); 
    
    // Lấy UID đang được chọn hiện tại trên Dropdown
    const uid = uidSelect ? uidSelect.value : "";
    
    console.log("Username sạch từ API:", authenticatedUsername);

    // 2. Gọi hàm loadGroups với thông tin chuẩn xác
    loadGroups(authenticatedUsername, uid, 1);

    // 3. Khởi tạo các thành phần UI khác độc lập
    initImageUploader();
    initUpdateGroupButton();
    initPostButton();

    // setInterval(() => {
    //     autoSyncGroupsToServer();
    // }, 5000);

    // ---------------------------------------------------------
    // BƯỚC 3: Đăng ký các Sự kiện Lắng nghe (Listeners)
    // ---------------------------------------------------------
    // Sự kiện Thay đổi UID trên Dropdown
    if (uidSelect) {
        uidSelect.addEventListener("change", (e) => {
            const currentUid = e.target.value;
            // Lúc này biến `authenticatedUsername` chắc chắn đã có giá trị từ API (ví dụ "admin")
            loadGroups(authenticatedUsername, currentUid, 1);
        });
    }

    // Sự kiện Đăng xuất
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                await fetchWithAuth('/api/v1/logout', { method: 'POST' });
            } catch (err) {
                console.error("Lỗi gọi API logout:", err);
            } finally {
                localStorage.removeItem('access_token');
                sessionStorage.removeItem('access_token');
                window.location.href = "/login";
            }
        });
    }
});