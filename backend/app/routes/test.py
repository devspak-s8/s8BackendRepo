from fastapi import APIRouter, HTTPException
from bson import ObjectId

test_router = APIRouter()

@test_router.post("/make-client/{user_id}")
async def make_client(user_id: str):
    result = await user_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": "Client"}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or already Client")

    return {"msg": "✅ User role updated to Client"}