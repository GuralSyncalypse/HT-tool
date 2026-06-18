// main.js
import { checkAuthOrRedirect, fetchWithAuth, handleLogout } from "./auth.js"; 
import { loadActiveAccounts, loadGroups } from "./groups.js";
import { initImageUploader } from "./imageUploader.js"; 
import { initPostButton, initUpdateGroupButton } from "./bot.js"; 

document.addEventListener("DOMContentLoaded", async () => {
    // 1. Chặn ngay lập tức nếu không có token khi vừa load xong DOM
    const token = checkAuthOrRedirect();
    if (!token) return; // Dừng thực thi các dòng dưới nếu đang bị redirect về /login

    // --- KHAI BÁO CÁC PHẦN TỬ UI ---
    const guestZone = document.getElementById('auth-guest-zone');
    const userZone = document.getElementById('auth-user-zone');
    const logoutBtn = document.getElementById('btn-logout-ui');
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

    // --- KHỞI TẠO LOGIC APP ---
    await loadActiveAccounts(); 
    const uid = uidSelect ? uidSelect.value : "";
    loadGroups(authenticatedUsername, uid, 1);

    initImageUploader();
    initUpdateGroupButton();
    initPostButton();

    // --- SỰ KIỆN ---
    if (uidSelect) {
        uidSelect.addEventListener("change", (e) => {
            loadGroups(authenticatedUsername, e.target.value, 1);
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
});