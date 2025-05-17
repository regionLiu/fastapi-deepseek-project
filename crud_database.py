from database import db
from models import RequestDocument

# User


def update_token(user_id: str, token: str):
    try:
        token_data = db.users.update_one(
            {"user_id": user_id}, {"$set": {"token": token}})
        if token_data:
            return True
        else:
            return False
    except Exception as e:
        raise e


def verify_database_token(token: str):
    try:
        user = db.users.find_one({"token": token})
        if user:
            return user
        else:
            return None
    except Exception as e:
        raise e


# AI Request Document
async def insert_request_document(user_id: str, request_type: str, request_content: str, response_content: str):
    try:

        request_document = {
            "user_id": user_id,
            "request_type": request_type,
            "request_content": request_content,
            "response_content": response_content,

        }
        insert_data = db.request_documents.insert_one(request_document)
        return insert_data
    except Exception as e:
        raise e


async def crud_userfile_list(user_id: str):
    try:
        user_data = []
        user_file_list = db.request_documents.find({"user_id": user_id})
        if user_file_list:
            for _ in user_file_list:
                user_data.append({
                    "request_content": _.get("request_content"),
                    "response_content": _.get("response_content"),
                    "created_at": _.get("created_at"),
                })
        if user_data:
            for _ in range(len(user_data)):
                user_data[_]["id"] = _+1
        return user_data
    except Exception as e:
        raise e
