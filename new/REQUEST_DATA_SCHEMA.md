# Request Data JSON Schema Documentation

Khi tạo request với các loại khác nhau, field `request_data` phải chứa JSON string với format như sau:

## 1. SPLIT_HOUSEHOLD

Tách hộ khẩu - tạo hộ mới và di chuyển các thành viên.

### Required Fields:
```json
{
  "old_household_id": 1,
  "new_owner_id": 5,
  "moving_resident_ids": [5, 6, 7],
  "new_address": "123 Đường ABC, Phường XYZ",
  "new_household_code": "HH-2024-NEW-001"
}
```

### Optional Fields:
```json
{
  "replacement_owner_id": 2
}
```

**Lưu ý:** 
- Nếu `new_owner_id` là chủ hộ hiện tại của `old_household_id`, **bắt buộc** phải cung cấp `replacement_owner_id`
- `replacement_owner_id` KHÔNG được nằm trong `moving_resident_ids`
- `new_household_code` phải là duy nhất (unique)

---

## 2. JOIN_HOUSEHOLD

Thêm người vào hộ khẩu hiện có.

### Required Fields:
```json
{
  "resident_id": 10,
  "target_household_id": 3,
  "relation_to_owner": "MEMBER"
}
```

**Relation values:** HEAD, MEMBER, WIFE, HUSBAND, SON, DAUGHTER, etc.

---

## 3. NEW_HOUSEHOLD

Tạo hộ khẩu mới.

### Required Fields:
```json
{
  "household_code": "HH-2024-XYZ-001",
  "owner_id": 15,
  "address": "456 Đường DEF, Quận GHI"
}
```

**Lưu ý:**
- `household_code` phải là duy nhất
- `owner_id` phải là một resident đã tồn tại

---

## 4. HOUSEHOLD_UPDATE

Cập nhật thông tin hộ khẩu.

### Required Fields:
```json
{
  "household_id": 2
}
```

### Optional Fields (ít nhất 1):
```json
{
  "address": "Địa chỉ mới",
  "household_code": "Mã hộ mới",
  "owner_id": 20
}
```

**Lưu ý:**
- Nếu thay đổi `owner_id`, người mới phải là thành viên của hộ hiện tại
- Nếu thay đổi `household_code`, mã mới phải unique

---

## 5. PERSON_UPDATE

Cập nhật thông tin cá nhân.

### Required Fields:
```json
{
  "resident_id": 8
}
```

### Optional Fields (ít nhất 1):
```json
{
  "full_name": "Nguyễn Văn A",
  "dob": "1990-01-15",
  "gender": "MALE",
  "cid": "001234567890",
  "relation_to_owner": "SON",
  "status": "PERMANENT"
}
```

**Gender values:** MALE, FEMALE

**Status values:** PERMANENT, TEMPORARY_ABSENT, TEMPORARY_RESIDENT, MOVED_OUT

**Lưu ý:**
- `cid` (Citizen ID) phải là unique
- `dob` format: YYYY-MM-DD

---

## Example: Tạo Request via API

### 1. Tạo yêu cầu tách hộ

```bash
curl -X POST http://localhost:8000/api/requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "request_type": "SPLIT_HOUSEHOLD",
    "title": "Yêu cầu tách hộ khẩu",
    "description": "Tách hộ do thành lập gia đình riêng",
    "request_data": "{\"old_household_id\": 1, \"new_owner_id\": 5, \"moving_resident_ids\": [5, 6], \"new_address\": \"123 ABC\", \"new_household_code\": \"HH-NEW-001\"}",
    "household_id": 1,
    "resident_id": 5
  }'
```

### 2. Duyệt yêu cầu (Admin/Leader)

```bash
curl -X PUT http://localhost:8000/api/requests/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "status": "APPROVED",
    "approval_note": "Đã kiểm tra và đồng ý"
  }'
```

Khi request được APPROVED, hệ thống sẽ tự động:
- Tạo hộ mới với mã `HH-NEW-001`
- Di chuyển residents có ID 5, 6 sang hộ mới
- Cập nhật owner của hộ mới là resident ID 5
- Ghi log vào bảng `change_history`

---

## Error Handling

Nếu có lỗi khi xử lý (ví dụ: mã hộ đã tồn tại, resident không thuộc hộ cũ, v.v.):
- Transaction sẽ tự động rollback
- Request status vẫn là PENDING
- API trả về lỗi chi tiết

```json
{
  "detail": "Household code HH-NEW-001 already exists"
}
```
