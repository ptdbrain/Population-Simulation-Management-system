# BÁO CÁO ĐÁNH GIÁ CODE BACKEND

## 📋 TỔNG QUAN
Đánh giá code backend của hệ thống PSMS (Population Simulation Management System) - Hệ thống quản lý hộ khẩu & phản ánh.

---

## ✅ ĐIỂM MẠNH

1. **Cấu trúc dự án tốt**: Tách biệt rõ ràng giữa models, routers, schemas, crud
2. **Sử dụng FastAPI**: Framework hiện đại, hiệu năng cao
3. **Có hệ thống phân quyền**: Role-based access control với permissions
4. **Có refresh token**: Bảo mật tốt hơn với token rotation
5. **Sử dụng SQLAlchemy ORM**: Code dễ đọc và maintain

---

## ⚠️ VẤN ĐỀ NGHIÊM TRỌNG

### 1. **BẢO MẬT - Hardcoded Credentials**
**File**: `BE/app/core/config.py`
- ❌ Hardcoded database credentials trong code
- ❌ SECRET_KEY yếu và hardcoded
- **Rủi ro**: Lộ thông tin nhạy cảm, dễ bị tấn công

**Giải pháp**: Sử dụng biến môi trường (.env file)

### 2. **TRÙNG LẶP CODE - Hai file xử lý JWT**
**Files**: `BE/app/auth_jwt.py` và `BE/app/core/security.py`
- ❌ Có 2 file xử lý JWT/auth với chức năng trùng lặp
- ❌ `auth_jwt.py` sử dụng `datetime.datetime.utcnow()` (sai cú pháp)
- ❌ Import không nhất quán

**Giải pháp**: Chỉ giữ 1 file, thống nhất sử dụng `core/security.py`

### 3. **LỖI CẤU HÌNH - Thiếu biến trong Settings**
**File**: `BE/app/core/security.py`
- ❌ Sử dụng `settings.ACCESS_EXPIRE_MINUTES` nhưng config có `ACCESS_TOKEN_EXPIRE_MINUTES`
- ❌ Sử dụng `settings.REFRESH_EXPIRE_DAYS` nhưng không được định nghĩa trong config

**Giải pháp**: Thêm `REFRESH_EXPIRE_DAYS` vào config và sửa tên biến cho nhất quán

### 4. **LỖI MODEL - Trường bị thiếu/trùng lặp**
**File**: `BE/app/models.py`
- ❌ `ComplaintReport.report_at` bị khai báo 2 lần (dòng 116 và 119)
- ❌ `Person` model không có trường `id_number` nhưng được dùng trong code
- ❌ `User` model không có trường `phone` nhưng được dùng trong code

**Giải pháp**: Thêm các trường còn thiếu vào model

---

## 🔴 VẤN ĐỀ QUAN TRỌNG

### 5. **LỖI IMPORT - Đường dẫn sai**
**File**: `BE/app/Routers/auth.py` (dòng 69)
```python
from core.security import _hash_refresh_token  # SAI
```
**Giải pháp**: Sửa thành `from app.core.security import _hash_refresh_token`

### 6. **LỖI LOGIC - user_id=None trong logout**
**File**: `BE/app/Routers/auth.py` (dòng 103)
```python
revoked = revoke_refresh_token(db, refresh_token, user_id=None)
```
- ❌ Hàm `revoke_refresh_token` cần `user_id` nhưng truyền `None`
- **Giải pháp**: Lấy user_id từ token hoặc yêu cầu authentication

### 7. **LỖI SQL QUERY - Tên cột không khớp**
**File**: `BE/app/deps.py` (dòng 50)
```python
WHERE ur.user_id = :user_id AND p.name = :permission_name
```
- ❌ Query dùng `p.name` nhưng parameter là `permission_name`
- ❌ Trong model `Permission`, trường là `code` chứ không phải `name`
- **Giải pháp**: Sửa query để dùng `p.code` và parameter `permission_code`

### 8. **TRÙNG LẶP PREFIX - Route path**
**File**: `BE/app/Routers/users.py`
- ❌ Router có `prefix="/api/users"` nhưng route cũng có `/api/users`
- ❌ Kết quả: URL thực tế là `/api/users/api/users`
- **Giải pháp**: Bỏ prefix hoặc bỏ `/api/users` trong decorator

---

## ⚡ VẤN ĐỀ HIỆU NĂNG

### 9. **N+1 Query Problem**
- ❌ Trong `auth.py`, query roles và permissions riêng biệt
- ❌ Có thể tối ưu bằng JOIN hoặc eager loading
- **Giải pháp**: Sử dụng `joinedload` hoặc viết query JOIN hiệu quả hơn

### 10. **Thiếu Indexing**
- ⚠️ Một số trường thường xuyên query nhưng chưa có index
- **Giải pháp**: Thêm index cho các trường: `Person.current_household_id`, `Complaint.status`, etc.

---

## 🛡️ VẤN ĐỀ XỬ LÝ LỖI

### 11. **Thiếu Error Handling**
- ⚠️ Nhiều endpoint không có try-catch
- ⚠️ Transaction rollback không đầy đủ
- **Ví dụ**: `households.py` có rollback nhưng không nhất quán

### 12. **Validation yếu**
- ⚠️ Password policy chỉ kiểm tra độ dài tối thiểu
- ⚠️ Không validate email format
- ⚠️ Không validate date range (from_date < to_date)

---

## 📝 VẤN ĐỀ CODE QUALITY

### 13. **Inconsistent Naming**
- ⚠️ Một số file dùng `Schemas.py` (chữ S hoa), nên đổi thành `schemas.py`
- ⚠️ Mix giữa tiếng Việt và tiếng Anh trong comments

### 14. **Thiếu Type Hints**
- ⚠️ Một số function thiếu return type hints
- **Ví dụ**: `create_user` trong `crud.py`

### 15. **Magic Numbers/Strings**
- ⚠️ Hardcoded values như `"citizen"`, `60 * 24`
- **Giải pháp**: Đưa vào constants hoặc config

---

## 🔧 KHUYẾN NGHỊ CẢI THIỆN

### Ngay lập tức (Critical):
1. ✅ Sửa hardcoded credentials → dùng .env
2. ✅ Thống nhất JWT handling → chỉ dùng `core/security.py`
3. ✅ Sửa lỗi model (thêm trường thiếu, xóa trùng lặp)
4. ✅ Sửa lỗi import và logic trong `auth.py`
5. ✅ Sửa query trong `deps.py`

### Quan trọng (High Priority):
6. ✅ Sửa prefix trùng lặp trong routers
7. ✅ Thêm error handling đầy đủ
8. ✅ Cải thiện validation

### Nên làm (Medium Priority):
9. ✅ Tối ưu queries (tránh N+1)
10. ✅ Thêm indexes cho database
11. ✅ Cải thiện code quality (naming, type hints)

---

## 📊 ĐIỂM ĐÁNH GIÁ TỔNG THỂ

| Tiêu chí | Điểm | Ghi chú |
|----------|------|---------|
| Bảo mật | 4/10 | Hardcoded credentials, thiếu validation |
| Code Quality | 6/10 | Có cấu trúc tốt nhưng nhiều lỗi logic |
| Performance | 6/10 | Có thể tối ưu queries |
| Error Handling | 5/10 | Thiếu xử lý lỗi đầy đủ |
| Maintainability | 7/10 | Cấu trúc tốt, dễ maintain |
| **TỔNG ĐIỂM** | **5.6/10** | **Cần cải thiện ngay** |

---

## 🎯 KẾT LUẬN

Code có **cấu trúc tốt** và **hướng đi đúng**, nhưng có **nhiều lỗi nghiêm trọng** về:
- 🔴 **Bảo mật**: Hardcoded credentials
- 🔴 **Logic**: Nhiều lỗi import, query, model
- 🟡 **Code Quality**: Cần cải thiện error handling và validation

**Khuyến nghị**: Sửa các lỗi Critical trước khi deploy production.

