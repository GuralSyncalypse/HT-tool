// groups.js
import { fetchWithAuth } from "./main.js";

// Đảm bảo lấy chính xác các Element từ DOM
const selectUid = document.getElementById("select-uid");
const container = document.getElementById("group-container");

// ==========================================
// KHAI BÁO BIẾN TRẠNG THÁI TOÀN CỤC (GLOBAL STATE)
// ==========================================
let allGroups = [];
let currentPage = 1;
const pageSize = 10;
let totalGroupsCount = 0; 

// Sửa lỗi: Khai báo bộ nhớ đệm global chuẩn bằng từ khóa let
let currentUsername = "";
let currentUid = "";

/**
 * Hàm gọi API lấy dữ liệu theo từng trang
 * @param {string} username 
 * @param {string} uid 
 * @param {number} page - Trang cần lấy (mặc định là 1)
 */
export async function loadGroups(username, uid, page = 1) {
    // BẢO VỆ BIẾN: Khống chế hoàn toàn lỗi UI bị render chậm hiển thị chữ "..."
    if ((!username || username === "..." || username.trim() === "") && currentUsername) {
        username = currentUsername;
    }
    if ((!uid || uid.trim() === "") && currentUid) {
        uid = currentUid;
    }

    if (!uid) {
        renderEmptyState();
        return;
    }

    // Ghi đè cập nhật vào bộ nhớ cache global
    currentUsername = username;
    currentUid = uid;
    currentPage = page;

    console.log(`🚀 Gọi API chuẩn với Username: ${username} | UID: ${uid} | Page: ${page}`);

    try {
        const params = new URLSearchParams({
            uid: uid,
            username: username,
            page: page.toString(),
            page_size: pageSize.toString()
        });

        // Sửa lỗi: Sử dụng fetchWithAuth thay vì fetch thuần để đính kèm Token
        const response = await fetchWithAuth(`/api/get-groups?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const result = await response.json(); 
        const groups = result.data || result; 
        totalGroupsCount = result.total || groups.length; 

        if (groups && groups.length > 0) {
            allGroups = groups; 
            renderPage(); 
        } else {
            renderEmptyState();
        }
    } catch (error) {
        console.error("Lỗi tại loadGroups:", error);
        renderEmptyState();
    }
}

function renderPagination() {
    const pagination = document.getElementById("pagination");
    if (!pagination) return;
    
    pagination.innerHTML = "";

    const totalPages = Math.ceil(totalGroupsCount / pageSize);
    if (totalPages <= 1) return; // Chỉ có 1 trang thì không hiện

    // Mảng chứa các số trang sẽ được hiển thị ra màn hình
    let pagesToShow = [];

    // Số lượng trang xung quanh trang hiện tại muốn hiển thị (Ví dụ: trang hiện tại là 5, hiển thị thêm số 4 và 6)
    const delta = 1; 

    for (let i = 1; i <= totalPages; i++) {
        // Luôn hiển thị trang đầu, trang cuối, và các trang nằm trong khoảng delta của currentPage
        if (
            i === 1 || 
            i === totalPages || 
            (i >= currentPage - delta && i <= currentPage + delta)
        ) {
            pagesToShow.push(i);
        }
    }

    // Tiến hành vẽ các nút dựa trên mảng pagesToShow và chèn dấu "..."
    let lastPage = 0;
    
    pagesToShow.forEach(page => {
        // Nếu khoảng cách giữa 2 trang lớn hơn 1, chèn một nút dấu ba chấm "..."
        if (lastPage !== 0 && page - lastPage > 1) {
            const dots = document.createElement("span");
            dots.textContent = "...";
            dots.className = "px-3 py-1 text-gray-400 mx-1 align-middle select-none";
            pagination.appendChild(dots);
        }

        // Tạo nút bấm số trang
        const btn = document.createElement("button");
        btn.setAttribute("type", "button");
        btn.textContent = page;

        // CSS Tailwind cho nút bấm
        btn.className = page === currentPage
            ? "px-3 py-1 bg-blue-500 text-white rounded font-medium mx-1 cursor-pointer shadow-xs transition"
            : "px-3 py-1 border border-gray-200 rounded text-gray-600 hover:bg-gray-50 mx-1 cursor-pointer transition";

        // Gắn sự kiện click gọi API lấy trang mới
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            loadGroups(currentUsername, currentUid, page);
        });

        pagination.appendChild(btn);
        lastPage = page;
    });
}

function renderPage() {
    const groupContainer = document.getElementById("group-container");
    if (!groupContainer) return;

    groupContainer.innerHTML = "";
    groupContainer.scrollTop = 0; // Tự động cuộn lên đầu danh sách khi qua trang mới

    allGroups.forEach(group => {
        const row = document.createElement("div");
        row.className = "grid grid-cols-12 text-xs text-gray-600 px-2 py-3 items-center hover:bg-gray-50 transition w-full";
        
        row.innerHTML = `
            <div class="col-span-6 min-w-0">
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 flex-shrink-0">
                        <i class="fa-solid fa-users"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <a href="${group.group_url}" target="_blank" class="font-semibold text-gray-800 hover:text-blue-600 block truncate">
                            ${group.group_name}
                        </a>
                        <div class="text-[11px] text-gray-400 mt-1 truncate">
                            Group ID: ${group.group_id}
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-2 text-center text-gray-400">-</div>
            <div class="col-span-2 text-center text-gray-400">-</div>
            <div class="col-span-1 text-center text-gray-400">-</div>

            <div class="col-span-1 flex justify-center">
                <button
                    type="button"
                    class="text-gray-400 hover:text-blue-600 p-1 rounded hover:bg-gray-100 transition z-10"
                    onclick="navigator.clipboard.writeText('${group.group_id}'); alert('Đã copy ID: ${group.group_id}');">
                    <i class="fa-regular fa-copy"></i>
                </button>
            </div>
        `;
        groupContainer.appendChild(row);
    });

    renderPagination();
}

export function renderEmptyState() {
    const groupContainer = document.getElementById("group-container");
    if (!groupContainer) return;
    
    groupContainer.innerHTML = `
        <div class="flex-1 flex flex-col items-center justify-center py-12">
            <span class="text-sm font-bold text-gray-800">
                Không tìm thấy nhóm
            </span>
        </div>
    `;
    
    // Clear luôn cả thanh phân trang nếu không có dữ liệu
    const pagination = document.getElementById("pagination");
    if (pagination) pagination.innerHTML = "";
}

export async function loadActiveAccounts() {
    try {
        const response = await fetchWithAuth("/api/active-accounts");
        const data = await response.json();

        if (!selectUid) return;
        selectUid.innerHTML = "";

        if (!data.uids?.length) {
            renderEmptyState();
            return;
        }

        data.uids.forEach(uid => {
            const option = document.createElement("option");
            option.value = uid;
            option.textContent = `Facebook UID: ${uid}`;
            selectUid.appendChild(option);
        });

    } catch (error) {
        console.error("Lỗi tại loadActiveAccounts:", error);
        renderEmptyState();
    }
}

/**
 * Hàm gửi toàn bộ danh sách groups hiện tại lên Backend
 */
export async function sendGroupsToServer() {
    // 1. Kiểm tra xem bộ nhớ đệm hiện tại có group nào không
    if (!allGroups || allGroups.length === 0) {
        alert("Danh sách nhóm hiện tại đang trống, không thể gửi!");
        return;
    }

    try {
        console.log("Đang gửi danh sách groups lên server...", allGroups);

        // 2. Gọi API POST truyền mảng allGroups qua Body dạng JSON
        const response = await fetchWithAuth('/api/groups/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(allGroups) // Chuyển mảng Object thành chuỗi JSON body
        });

        if (!response.ok) {
            throw new Error(`Server báo lỗi: ${response.status}`);
        }

        const result = await response.json();
        console.log("Kết quả từ server:", result);
        alert(`Thành công: ${result.message}`);

    } catch (err) {
        console.error("Lỗi khi truyền danh sách groups lên endpoint:", err);
        alert("Có lỗi xảy ra khi gửi dữ liệu lên server!");
    }
}

// Biến cờ hiệu để tránh việc "đá nhau" nếu mạng chậm (API trước chưa xong mà 5s sau đã gọi tiếp)
let isSyncing = false;

/**
 * Hàm tự động gửi allGroups lên backend mỗi 5 giây (Không cần nút bấm)
 */
export async function autoSyncGroupsToServer() {
    // Nếu danh sách trống hoặc đang có một tiến trình gửi khác đang chạy thì bỏ qua
    if (!allGroups || allGroups.length === 0 || isSyncing) {
        return; 
    }

    try {
        isSyncing = true; // Khóa lại để không cho lượt 5s kế tiếp chạy đè lên
        console.log("🔄 [Auto-Sync] Đang tự động gửi danh sách groups lên server...", allGroups);

        const response = await fetchWithAuth('/api/groups/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(allGroups) // Truyền thẳng mảng allGroups global của bạn
        });

        if (!response.ok) {
            throw new Error(`Server báo lỗi: ${response.status}`);
        }

        const result = await response.json();
        console.log("✅ [Auto-Sync] Đồng bộ thành công:", result);

    } catch (err) {
        console.error("❌ [Auto-Sync] Lỗi đồng bộ tự động:", err);
    } finally {
        isSyncing = false; // Mở khóa để lượt 5s tiếp theo có thể chạy tiếp
    }
}