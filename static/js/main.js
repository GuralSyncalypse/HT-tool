// main.js
import { loadActiveAccounts, loadGroups } from "./groups.js";
import { initBotButton } from "./bot.js";
import { initImageUploader } from "./imageUploader.js"; // Import file xử lý ảnh

document.addEventListener("DOMContentLoaded", () => {

    // Khởi tạo các logic hệ thống cũ
    loadActiveAccounts();
    initBotButton();

    document.getElementById("select-uid").addEventListener("change", (e) => {
        loadGroups(e.target.value);
    });

    // Khởi tạo logic quản lý ảnh độc lập
    initImageUploader();
    
});