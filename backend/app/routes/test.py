from fastapi import APIRouter, HTTPException
from bson import ObjectId
from s8.db.database import user_collection
test_router = APIRouter()

@test_router.post("/make-dev/{user_id}")
async def make_dev(user_id: str):
    result = await user_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": "Client"}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or already Client")

    return {"msg": "✅ User role updated to Client"}
