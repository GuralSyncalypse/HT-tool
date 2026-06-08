// groups.js
import { fetchWithAuth } from "./main.js";

// Đảm bảo lấy chính xác các Element từ DOM
const selectUid = document.getElementById("select-uid");
const container = document.getElementById("group-container");

// ==========================================
// KHAI BÁO BIẾN TRẠNG THÁI TOÀN CỤC (GLOBAL STATE)
// ==========================================
export let selectedGroups = [];
export let displayGroups = [];

// Sức chứa của 1 trang
let currentPage = 1;
const pageSize = 10;

let totalGroupsCount = 0; 

let currentUsername = "";
let currentUid = "";

/**
 * Hàm gọi API lấy dữ liệu theo từng trang
 * @param {string} username 
 * @param {string} uid 
 * @param {number} page - Trang cần lấy (mặc định là 1)
 */
export async function loadGroups(username, uid, page = 1) {
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

    currentUsername = username;
    currentUid = uid;
    currentPage = page;

    console.log(`🚀 Gọi API với Username: ${username} | UID: ${uid} | Page: ${page}`);

    try {
        const params = new URLSearchParams({
            uid: uid,
            username: username,
            page: page.toString(),
            page_size: pageSize.toString()
        });

        const response = await fetchWithAuth(`/api/v1/get-groups?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const result = await response.json(); 
        const groups = result.data || result; 
        totalGroupsCount = result.total || groups.length; 

        if (groups && groups.length > 0) {
            displayGroups = groups; 
            
            // Tiến hành render danh sách chính và phân trang
            renderPage(); 
            renderPagination();
        } else {
            renderEmptyState();
        }
    } catch (error) {
        console.error("Lỗi tại loadGroups:", error);
        renderEmptyState();
    }
}

/**
 * Hàm render danh sách group chính ở trang hiện tại
 */
/**
 * Hàm render danh sách group chính ở trang hiện tại
 * ĐÃ SỬA: Tự động kiểm tra trạng thái chọn để giữ dấu tick xuyên trang
 */
function renderPage() {
    const container = document.getElementById("group-container");
    if (!container) return;
    container.innerHTML = "";

    displayGroups.forEach(group => {
        const row = document.createElement("div");
        row.className = "grid grid-cols-12 items-center text-sm text-gray-700 px-2 py-3 hover:bg-gray-50 transition-colors";

        // 🌟 BƯỚC QUAN TRỌNG: Kiểm tra xem group này ĐÃ TỒN TẠI trong mảng selectedGroups hay chưa
        const isChecked = selectedGroups.some(g => g.group_id === group.group_id);

        // Chèn thuộc tính ${isChecked ? "checked" : ""} vào thẻ input
        row.innerHTML = `
            <div class="col-span-6 min-w-0">
                <div class="flex items-start gap-3">
                    <div class="flex items-center h-10 flex-shrink-0">
                        <input 
                            type="checkbox" 
                            value="${group.group_id}"
                            class="group-checkbox w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
                            ${isChecked ? "checked" : ""} 
                            data-id="${group.group_id}"
                        >
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

        // Gắn sự kiện thay đổi trạng thái cho checkbox
        const checkbox = row.querySelector(".group-checkbox");
        checkbox.addEventListener("change", (e) => {
            handleCheckboxChange(group, e.target.checked);
        });

        container.appendChild(row);
    });

    // 🌟 ĐẶT Ở ĐÂY: Sau khi toàn bộ các hàng của trang mới đã được vẽ xong
    updateMasterCheckboxState();
}

/**
 * Xử lý logic Thêm/Xóa group khỏi SelectedList khi click checkbox
 */
function handleCheckboxChange(group, isChecked) {
    if (isChecked) {
        // Nếu chưa có trong list thì push vào
        if (!selectedGroups.some(g => g.group_id === group.group_id)) {
            selectedGroups.push(group);
        }
    } else {
        // Nếu uncheck thì lọc bỏ ra khỏi list
        selectedGroups = selectedGroups.filter(g => g.group_id !== group.group_id);
    }
    
    // Cập nhật lại UI của danh sách đã chọn bên ngoài
    renderSelectedList();
}


/**
 * Hàm render danh sách các Group đã chọn lên trên cùng (bên ngoài container)
 * Đã cấu hình rút ngắn tên nhóm để giao diện gọn gàng
 */
function renderSelectedList() {
    const selectedContainer = document.getElementById("selected-container");
    const selectedCountEl = document.getElementById("selected-count");
    if (!selectedContainer) return;

    // Cập nhật số lượng hiển thị cạnh checkbox tổng
    if (selectedCountEl) {
        selectedCountEl.textContent = selectedGroups.length;
    }

    selectedContainer.innerHTML = "";

    // MẶC ĐỊNH: Nếu không chọn gì -> Hiện "Mặc định: ALL"
    if (selectedGroups.length === 0) {
        selectedContainer.innerHTML = `
            <div class="text-xs text-gray-500 bg-gray-100 px-2.5 py-1.5 rounded-md inline-block font-medium italic">
                🌍 Mặc định: Chọn tất cả (ALL)
            </div>
        `;
        return;
    }

    // Nếu có chọn, sinh ra các Badge kèm nút hủy nhanh (x)
    const listWrapper = document.createElement("div");
    listWrapper.className = "flex flex-wrap gap-1.5 items-center";
    
    // Tạo text tiêu đề "Đã chọn (X):" cho giống ảnh của bạn
    const titleSpan = document.createElement("span");
    titleSpan.className = "text-xs font-bold text-gray-700 mr-1";
    titleSpan.textContent = `Đã chọn (${selectedGroups.length}):`;
    listWrapper.appendChild(titleSpan);

    selectedGroups.forEach(group => {
        // 🌟 LOGIC RÚT NGẮN TÊN: Lấy tên thật, nếu quá 15 ký tự thì cắt ngắn + "..."
        const rawName = group.group_name || `Nhóm ${group.group_id}`;
        const maxLength = 15; 
        const displayName = rawName.length > maxLength 
            ? rawName.substring(0, maxLength) + "..." 
            : rawName;

        const badge = document.createElement("span");
        // Thêm thuộc tính title để khi người dùng di chuột vào badge vẫn xem được đầy đủ tên nhóm gốc
        badge.setAttribute("title", rawName);
        badge.className = "inline-flex items-center gap-1 pl-2 pr-1 py-1 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100 transition-all";
        
        badge.innerHTML = `
            <span class="truncate select-none">${displayName}</span>
            <button type="button" class="text-blue-400 hover:bg-blue-200 hover:text-blue-900 rounded-xs p-0.5 transition-colors flex-shrink-0 cursor-pointer">
                <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        `;

        // Sự kiện click nút (x) để xóa nhanh trên Badge
        badge.querySelector("button").addEventListener("click", () => {
            selectedGroups = selectedGroups.filter(g => g.group_id !== group.group_id);
            renderSelectedList();
            renderPage(); // Vẽ lại trang hiện tại để đồng bộ bỏ tích checkbox
            updateMasterCheckboxState();
        });

        listWrapper.appendChild(badge);
    });

    selectedContainer.appendChild(listWrapper);
}

/**
 * Hàm phân trang giữ nguyên logic của bạn
 */
function renderPagination() {
    const pagination = document.getElementById("pagination");
    if (!pagination) return;
    
    pagination.innerHTML = "";
    const totalPages = Math.ceil(totalGroupsCount / pageSize);
    if (totalPages <= 1) return;

    let pagesToShow = [];
    const delta = 1; 

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - delta && i <= currentPage + delta)) {
            pagesToShow.push(i);
        }
    }

    let lastPage = 0;
    
    pagesToShow.forEach(page => {
        if (lastPage !== 0 && page - lastPage > 1) {
            const dots = document.createElement("span");
            dots.textContent = "...";
            dots.className = "px-3 py-1 text-gray-400 mx-1 align-middle select-none";
            pagination.appendChild(dots);
        }

        const btn = document.createElement("button");
        btn.setAttribute("type", "button");
        btn.textContent = page;
        btn.className = page === currentPage
            ? "px-3 py-1 bg-blue-500 text-white rounded font-medium mx-1 cursor-pointer shadow-xs transition"
            : "px-3 py-1 border border-gray-200 rounded text-gray-600 hover:bg-gray-50 mx-1 cursor-pointer transition";

        btn.addEventListener("click", (e) => {
            e.preventDefault();

            loadGroups(currentUsername, currentUid, page);
        });

        pagination.appendChild(btn);
        lastPage = page;
    });
}

/**
 * Hàm tự động bật/tắt Checkbox Tổng dựa trên các item của trang hiện tại
 */
function updateMasterCheckboxState() {
    const masterCheckbox = document.getElementById("master-checkbox");
    if (!masterCheckbox) return;

    // Nếu trang hiện tại không có dữ liệu, mặc định bỏ check
    if (displayGroups.length === 0) {
        masterCheckbox.checked = false;
        return;
    }

    // KIỂM TRA: Liệu TẤT CẢ các item của trang hiện tại đã nằm trong mảng selectedGroups chưa?
    const isAllCurrentPageSelected = displayGroups.every(group => 
        selectedGroups.some(g => g.group_id === group.group_id)
    );

    // Nếu đúng là toàn bộ trang đã được chọn -> Tích ô Master, ngược lại thì bỏ tích
    masterCheckbox.checked = isAllCurrentPageSelected;
}

// Chạy khởi tạo danh sách rỗng ban đầu (Hiện chữ Mặc định: ALL)
document.addEventListener("DOMContentLoaded", () => {
    renderSelectedList();

    const masterCheckbox = document.getElementById("master-checkbox");
    if (masterCheckbox) {
        masterCheckbox.addEventListener("change", (e) => {
            const isChecked = e.target.checked;

            if (isChecked) {
                // HÀNH ĐỘNG: CHỌN HẾT TRANG HIỆN TẠI
                displayGroups.forEach(group => {
                    // Nếu group này chưa có trong danh sách tổng thì mới push vào
                    if (!selectedGroups.some(g => g.group_id === group.group_id)) {
                        selectedGroups.push(group);
                    }
                });
            } else {
                // HÀNH ĐỘNG: BỎ CHỌN HẾT TRANG HIỆN TẠI
                // Chỉ lọc bỏ các group có group_id nằm trong trang hiện tại
                selectedGroups = selectedGroups.filter(g => 
                    !displayGroups.some(dg => dg.group_id === g.group_id)
                );
            }

            // Cập nhật lại giao diện
            renderSelectedList(); // Vẽ lại danh sách badge phía trên + cập nhật counter
            renderPage();         // Tích hoặc hủy tích các checkbox hàng dưới
        });
    }
});

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
        const response = await fetchWithAuth("/api/v1/active-accounts");
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

