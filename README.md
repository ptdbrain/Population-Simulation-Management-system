# Hệ thống quản lý hộ khẩu và nhân khẩu

Đây là một hệ thống web quản lý hộ khẩu và nhân khẩu được xây dựng với FastAPI (Python) cho backend và HTML/CSS/JavaScript cho frontend, sử dụng MongoDB làm cơ sở dữ liệu.

## Tính năng chính

### 1. Quản lý hộ khẩu và nhân khẩu
- Thêm, sửa, xóa thông tin hộ khẩu
- Thêm, sửa, xóa thông tin nhân khẩu
- Quản lý quan hệ gia đình
- Tìm kiếm thông tin nhanh chóng

### 2. Các hoạt động biến đổi nhân khẩu
- **Tách hộ**: Tạo hộ khẩu mới từ hộ khẩu hiện có
- **Tạm vắng**: Quản lý giấy tạm vắng khi nhân khẩu đi xa dài ngày
- **Tạm trú**: Quản lý giấy tạm trú cho nhân khẩu từ địa phương khác

### 3. Quản lý phản ánh và kiến nghị
- Ghi nhận phản ánh, kiến nghị của nhân dân
- Theo dõi trạng thái xử lý
- Ghi nhận phản hồi từ cơ quan có liên quan
- Thống kê theo trạng thái

### 4. Thống kê và báo cáo
- Thống kê nhân khẩu theo giới tính
- Thống kê nhân khẩu theo độ tuổi
- Thống kê phản ánh/kiến nghị theo trạng thái
- Xem lịch sử thay đổi nhân khẩu

## Cài đặt và chạy ứng dụng

### Yêu cầu hệ thống
- Python 3.8+
- MongoDB
- Node.js (tùy chọn, để chạy MongoDB)

### Bước 1: Cài đặt MongoDB
```bash
# Cài đặt MongoDB Community Edition
# Windows: Tải từ https://www.mongodb.com/try/download/community
# Ubuntu/Debian:
sudo apt-get install mongodb

# macOS với Homebrew:
brew install mongodb-community
```

### Bước 2: Cài đặt dependencies
```bash
# Cài đặt các package Python
pip install -r requirements.txt
```

### Bước 3: Cấu hình
1. Đảm bảo MongoDB đang chạy trên port 27017
2. Sao chép file `config.env` thành `.env` và chỉnh sửa các thông số nếu cần:
```bash
cp config.env .env
```

### Bước 4: Chạy ứng dụng
```bash
# Chạy server FastAPI
python main.py
```

Ứng dụng sẽ chạy tại: http://localhost:8000

## Cấu trúc dự án

```
├── main.py                 # File chính của FastAPI
├── requirements.txt        # Dependencies Python
├── config.env             # File cấu hình
├── static/                # Thư mục chứa frontend
│   ├── index.html         # Trang chủ
│   ├── style.css          # CSS styles
│   └── script.js          # JavaScript logic
└── README.md              # File hướng dẫn này
```

## API Endpoints

### Hộ khẩu
- `GET /api/households/` - Lấy danh sách hộ khẩu
- `POST /api/households/` - Tạo hộ khẩu mới
- `GET /api/households/{id}` - Lấy thông tin hộ khẩu
- `PUT /api/households/{id}` - Cập nhật hộ khẩu
- `DELETE /api/households/{id}` - Xóa hộ khẩu

### Nhân khẩu
- `GET /api/persons/` - Lấy danh sách nhân khẩu
- `POST /api/persons/` - Tạo nhân khẩu mới
- `GET /api/persons/{id}` - Lấy thông tin nhân khẩu
- `PUT /api/persons/{id}` - Cập nhật nhân khẩu
- `DELETE /api/persons/{id}` - Xóa nhân khẩu

### Tạm vắng
- `GET /api/temporary-absences/` - Lấy danh sách tạm vắng
- `POST /api/temporary-absences/` - Tạo tạm vắng mới

### Tạm trú
- `GET /api/temporary-residences/` - Lấy danh sách tạm trú
- `POST /api/temporary-residences/` - Tạo tạm trú mới

### Phản ánh/Kiến nghị
- `GET /api/feedbacks/` - Lấy danh sách phản ánh/kiến nghị
- `POST /api/feedbacks/` - Tạo phản ánh/kiến nghị mới
- `PUT /api/feedbacks/{id}` - Cập nhật phản ánh/kiến nghị

### Thống kê
- `GET /api/statistics/population-by-gender` - Thống kê theo giới tính
- `GET /api/statistics/population-by-age` - Thống kê theo độ tuổi
- `GET /api/statistics/feedbacks-by-status` - Thống kê phản ánh theo trạng thái

## Sử dụng ứng dụng

1. **Quản lý hộ khẩu**: Thêm, sửa, xóa thông tin hộ khẩu
2. **Quản lý nhân khẩu**: Thêm, sửa, xóa thông tin nhân khẩu
3. **Tạm vắng/Tạm trú**: Quản lý các trường hợp tạm vắng và tạm trú
4. **Phản ánh/Kiến nghị**: Ghi nhận và theo dõi phản ánh, kiến nghị
5. **Thống kê**: Xem các báo cáo thống kê

## Lưu ý

- Đảm bảo MongoDB đang chạy trước khi khởi động ứng dụng
- Ứng dụng sử dụng CORS để cho phép truy cập từ frontend
- Dữ liệu được lưu trữ trong MongoDB với database tên `household_management`
- Giao diện responsive, hỗ trợ cả desktop và mobile

## Phát triển thêm

Để phát triển thêm tính năng:

1. **Xác thực người dùng**: Thêm hệ thống đăng nhập/đăng ký
2. **Phân quyền**: Phân quyền cho tổ trưởng, tổ phó
3. **Xuất báo cáo**: Xuất báo cáo PDF/Excel
4. **Thông báo**: Hệ thống thông báo khi có thay đổi
5. **Lịch sử**: Theo dõi lịch sử thay đổi chi tiết
6. **API nâng cao**: Thêm pagination, filtering, sorting

## Hỗ trợ

Nếu gặp vấn đề, hãy kiểm tra:
1. MongoDB có đang chạy không
2. Port 8000 có bị chiếm dụng không
3. Các dependencies đã được cài đặt đầy đủ chưa
4. File cấu hình có đúng không
