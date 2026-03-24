from pymongo.database import Database
from app.models.user import UserInDB
from typing import Optional
from bson import ObjectId

class UserRepository:
    def __init__(self, database: Database):
        self.collection = database["users"]
        self.collection.create_index("email", unique=True)
    def create_user(self, user: UserInDB) -> UserInDB:
        user_dict = user.model_dump(by_alias=True, exclude={"id"})
        result = self.collection.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        return UserInDB(**user_dict)
    def find_by_email(self, email: str) -> Optional[UserInDB]:
        user_data = self.collection.find_one({"email": email})
        if user_data:
            return UserInDB(**user_data)
        return None
    def find_by_id(self, user_id: str) -> Optional[UserInDB]:
        try:
            oid = ObjectId(user_id)
        except:
            return None
        user_data = self.collection.find_one({"_id": oid})
        if user_data:
            return UserInDB(**user_data)
        return None
