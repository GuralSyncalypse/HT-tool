# 1. Sử dụng Python bản slim làm môi trường chạy code thuần túy
FROM python:3.11-slim

# 2. Đặt thư mục làm việc bên trong container
WORKDIR /app

# 3. Copy file danh sách thư viện vào trước
COPY requirements.txt .

# 4. Cài đặt các thư viện Python (nhớ thêm --no-cache-dir để image nhẹ nhất)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ code từ máy thật vào container
COPY . .

# 6. Lệnh khởi chạy worker của bạn
CMD ["python", "worker.py"]