// main.js
import { loadActiveAccounts, loadGroups } from "./groups.js";
import { initImageUploader } from "./imageUploader.js"; 
import { initPostButton } from "./bot.js"; // Import bình thường

document.addEventListener("DOMContentLoaded", () => {
    loadActiveAccounts();

    // 1. Khởi tạo uploader
    initImageUploader();

    // 2. Khởi tạo logic nút gửi bài
    initPostButton(); 

    document.getElementById("select-uid").addEventListener("change", (e) => {
        loadGroups(e.target.value);
    });
});