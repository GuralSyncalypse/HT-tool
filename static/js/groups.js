const selectUid = document.getElementById("select-uid");
const container = document.getElementById("group-container");
let allGroups = [];
let currentPage = 1;
const pageSize = 10;
 
export async function loadGroups(username, uid) {
    if (!uid) {
        renderEmptyState();
        return;
    }

    try {
        const response = await fetch(
            `/api/get-groups/${uid}?page=1&page_size=10`
        );

        const groups = await response.json();

        if (groups && groups.length > 0) {
            allGroups = groups;
            currentPage = 1;

            renderPage(currentPage);
        } else {
            renderEmptyState();
        }

    } catch (error) {
        console.error(error);
        renderEmptyState();
    }
}

function renderPagination() {

    const pagination = document.getElementById("pagination");

    const totalPages =
        Math.ceil(allGroups.length / pageSize);

    pagination.innerHTML = "";

    for (let i = 1; i <= totalPages; i++) {

        const btn = document.createElement("button");

        btn.textContent = i;

        btn.className =
            i === currentPage
            ? "px-3 py-1 bg-blue-500 text-white rounded"
            : "px-3 py-1 border rounded";

        btn.onclick = () => renderPage(i);

        pagination.appendChild(btn);
    }
}

function renderPage(page) {

    currentPage = page;

    const start = (page - 1) * pageSize;
    const end = start + pageSize;

    const pageGroups = allGroups.slice(start, end);

    container.innerHTML = "";

    pageGroups.forEach(group => {
        const row = document.createElement("div");

        row.className =
            "grid grid-cols-12 text-xs text-gray-600 px-2 py-3 items-center hover:bg-gray-50 transition";

        row.innerHTML = `
            <div class="col-span-6">
                <div class="flex items-start gap-3">

                    <div class="w-10 h-10 rounded-lg bg-blue-50
                                flex items-center justify-center
                                text-blue-600">
                        <i class="fa-solid fa-users"></i>
                    </div>

                    <div class="flex-1 min-w-0">

                        <a
                            href="${group.group_url}"
                            target="_blank"
                            class="font-semibold text-gray-800 hover:text-blue-600 block truncate">

                            ${group.group_name}

                        </a>

                        <div class="text-[11px] text-gray-400 mt-1">
                            Group ID: ${group.group_id}
                        </div>

                    </div>

                </div>
            </div>

            <div class="col-span-2 text-center text-gray-400">-</div>
            <div class="col-span-2 text-center text-gray-400">-</div>
            <div class="col-span-1 text-center text-gray-400">-</div>
            <div class="col-span-1 text-center text-gray-400">-</div>

            <button
                class="text-gray-400 hover:text-blue-600"
                onclick="navigator.clipboard.writeText('${group.group_id}')">
                <i class="fa-regular fa-copy"></i>
            </button>
        `;

        container.appendChild(row);
    });

    renderPagination();
}

export function renderEmptyState() {
    container.innerHTML = `
        <div class="flex-1 flex flex-col items-center justify-center py-12">
            <span class="text-sm font-bold text-gray-800">
                Không tìm thấy nhóm
            </span>
        </div>
    `;
}

export async function loadActiveAccounts() {
    try {
        const response = await fetch("/api/active-accounts");
        const data = await response.json();

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

        loadGroups(selectUid.value);

    } catch (error) {
        console.error(error);
        renderEmptyState();
    }
}