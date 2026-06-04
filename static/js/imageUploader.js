// imageUploader.js

// Quản lý state bằng Object để tránh ô nhiễm global và dễ mở rộng sau này
const uploaderState = {
    selectedFiles: [],
    blobUrls: new Map() // Dùng Map để quản lý cặp File -> Blob URL cho chuẩn xác
};

/**
 * Hàm khởi tạo logic quản lý và preview ảnh
 * @param {Object} options - Cấu hình các selector nếu cần
 */
export function initImageUploader() {
    const imageInput = document.getElementById('imageInput');
    const btnSelectImage = document.getElementById('btnSelectImage');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');

    if (!imageInput || !btnSelectImage || !imagePreviewContainer) {
        console.warn("Image Uploader: Thiếu các phần tử HTML cần thiết.");
        return;
    }

    // Kích hoạt input file khi bấm nút custom
    btnSelectImage.addEventListener('click', () => imageInput.click());

    // Lắng nghe sự kiện chọn file
    imageInput.addEventListener('change', function() {
        const files = Array.from(this.files);
        
        // Lọc trùng sơ bộ để tránh người dùng chọn trùng chính xác 1 file 2 lần
        const newFiles = files.filter(newFile => 
            !uploaderState.selectedFiles.some(oldFile => oldFile.name === newFile.name && oldFile.size === newFile.size)
        );

        if (newFiles.length === 0) {
            this.value = '';
            return;
        }

        uploaderState.selectedFiles = uploaderState.selectedFiles.concat(newFiles);
        
        // Render thêm các ảnh mới chứ không xóa đi render lại toàn bộ
        appendPreviews(newFiles, imagePreviewContainer, btnSelectImage);
        
        // Reset input để có thể chọn lại cùng 1 file sau đó
        this.value = ''; 
    });
}

/**
 * Hàm sinh và thêm các preview mới vào DOM (Tối ưu hiệu năng)
 */
function appendPreviews(files, container, button) {
    if (uploaderState.selectedFiles.length > 0) {
        button.classList.add('text-blue-500');
    }

    files.forEach((file) => {
        // Tạo định danh duy nhất cho từng file dựa trên name và size
        const fileId = btoa(encodeURIComponent(file.name)) + file.size; 
        const objectURL = URL.createObjectURL(file);
        
        // Lưu lại để quản lý revoke sau này
        uploaderState.blobUrls.set(fileId, objectURL);

        // Tạo thẻ bọc ngoài
        const itemDiv = document.createElement('div');
        itemDiv.className = "relative w-20 h-20 rounded-lg overflow-hidden border border-gray-200 group";
        itemDiv.dataset.fileId = fileId; // Gắn ID vào DOM để dễ tìm và xóa

        // Thẻ ảnh
        const img = document.createElement('img');
        img.src = objectURL;
        img.className = "w-full h-full object-cover";

        // Nút xóa
        const removeBtn = document.createElement('button');
        removeBtn.type = "button";
        removeBtn.className = "absolute top-1 right-1 bg-gray-900/60 hover:bg-gray-900/80 text-white rounded-full p-1 text-[10px] w-5 h-5 flex items-center justify-center transition cursor-pointer z-10";
        removeBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';

        // Sự kiện xóa: Xóa trực tiếp phần tử này khỏi DOM và State mà không re-render toàn bộ
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            removeImage(fileId, itemDiv, button);
        });

        itemDiv.appendChild(img);
        itemDiv.appendChild(removeBtn);
        container.appendChild(itemDiv);
    });
}

/**
 * Hàm xóa ảnh tận gốc (Xóa trên DOM, hủy Blob URL, xóa trong Array dữ liệu)
 */
function removeImage(fileId, elementToRemove, button) {
    // 1. Thu hồi Blob URL của riêng ảnh này để giải phóng bộ nhớ ngay lập tức
    if (uploaderState.blobUrls.has(fileId)) {
        URL.revokeObjectURL(uploaderState.blobUrls.get(fileId));
        uploaderState.blobUrls.delete(fileId);
    }

    // 2. Cập nhật lại mảng dữ liệu (Tìm đúng file dựa trên ID ảo)
    uploaderState.selectedFiles = uploaderState.selectedFiles.filter(file => {
        const currentId = btoa(encodeURIComponent(file.name)) + file.size;
        return currentId !== fileId;
    });

    // 3. Xóa phần tử khỏi giao diện (mượt mà, không bị chớp nháy các ảnh khác)
    elementToRemove.remove();

    // 4. Cập nhật trạng thái nút bấm nếu hết ảnh
    if (uploaderState.selectedFiles.length === 0) {
        button.classList.remove('text-blue-500');
    }
}

/**
 * Giải phóng toàn bộ bộ nhớ (Nên gọi khi chuyển trang hoặc submit thành công)
 */
export function resetUploader(button, container) {
    uploaderState.blobUrls.forEach(url => URL.revokeObjectURL(url));
    uploaderState.blobUrls.clear();
    uploaderState.selectedFiles = [];
    if (container) container.innerHTML = '';
    if (button) button.classList.remove('text-blue-500');
}

/**
 * Lấy ra danh sách file hiện tại để gửi lên server (API FormData)
 * @returns {File[]} Mảng các file ảnh đã chọn
 */
export function getSelectedFiles() {
    return uploaderState.selectedFiles;
}