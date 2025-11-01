# app/utils.py
from fastapi.responses import JSONResponse

def error_response(status_code:int, message:str):
    return JSONResponse(status_code=status_code, content={"detail": message}) # trả về phản hồi JSON với mã trạng thái và thông điệp lỗi
