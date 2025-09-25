# # app/routes/dashboard_router.py
# from fastapi import APIRouter, Depends
# from s8.service.dashboard_service import get_dashboard_overview

# from app.middleware.rbac import get_current_user

# dashboard_router = APIRouter(tags=["Dashboard"])

# @dashboard_router.get("/overview")
# async def dashboard_overview(current_user: dict = Depends(get_current_user)):
#     user_id = str(current_user["_id"])
#     return await get_dashboard_overview(user_id)


# routes/client_dashboard.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
from bson import ObjectId

from s8.db.database import project_collection, booking_collection, user_collection # Your MongoDB connection
from app.middleware.rbac import get_current_client  # JWT dependency

from app.schemas.dashboard import (
    ClientDashboardResponse,
    FeedResponse,
    ProjectFeedItem,
    FeedPagination,
    BookingSummary,
    RecentBooking
)

router = APIRouter()

@router.get("/api/client/dashboard", response_model=ClientDashboardResponse)
async def get_client_dashboard(
    cursor: Optional[str] = Query(None, description="Pagination cursor (last project ID)"),
    limit: int = Query(10, ge=1, le=50, description="Number of projects per page"),
    current_client: dict = Depends(get_current_client)
):
    client_id = current_client["_id"]

    # ---------------------------
    # 1️⃣ Fetch client profile
    # ---------------------------
    client = await user_collection.find_one({"_id": ObjectId(client_id), "role": "client"})

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    preferred_services = client.get("preferred_services", [])

    # ---------------------------
    # 2️⃣ Query developer projects
    # ---------------------------
    query = {"serviceType": {"$in": preferred_services}}

    if cursor:
        try:
            query["_id"] = {"$lt": ObjectId(cursor)}
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    project_cursor = project_collection.find(query).sort("created_at", -1).limit(limit)
    projects = await project_cursor.to_list(length=limit)

    feed_projects = []
    for p in projects:
        try:
            feed_projects.append(ProjectFeedItem(
                projectId=str(p["_id"]),
                title=p.get("name", "No Title"),
                summary=(p.get("description") or "")[:150],
                techStack=p.get("tech_stack", []),
                serviceType=p.get("serviceType"),
                postedAt=p.get("created_at") or datetime.utcnow(),
                developer=p.get("developer_info")  # Optional nested dev info
            ))
        except Exception:
            continue  # skip malformed project

    next_cursor = str(projects[-1]["_id"]) if projects else None
    feed = FeedResponse(
        projects=feed_projects,
        pagination=FeedPagination(
            nextCursor=next_cursor,
            hasMore=True if next_cursor else False
        )
    )

    # ---------------------------
    # 3️⃣ Booking summary
    # ---------------------------
    try:
        bookings = await booking_collection.find({"clientId": str(client_id)}).to_list(None)
    except Exception:
        bookings = []

    total = len(bookings)
    active = sum(1 for b in bookings if b.get("status") == "Active")
    completed = sum(1 for b in bookings if b.get("status") == "Completed")

    booking_summary = BookingSummary(
        totalBookings=total,
        activeBookings=active,
        completedBookings=completed
    )

    # ---------------------------
    # 4️⃣ Recent bookings (limit 5)
    # ---------------------------
    try:
        recent = await booking_collection.find({"clientId": str(client_id)}) \
                                   .sort("startDate", -1) \
                                   .limit(5).to_list(length=5)
    except Exception:
        recent = []

    recent_bookings = []
    for b in recent:
        try:
            recent_bookings.append(RecentBooking(
                bookingId=str(b["_id"]),
                devName=b.get("devName", "Unknown"),
                status=b.get("status", "Pending"),
                startDate=b.get("startDate") or datetime.utcnow(),
                endDate=b.get("endDate")
            ))
        except Exception:
            continue

    # ---------------------------
    # 5️⃣ Return full dashboard response
    # ---------------------------
    return ClientDashboardResponse(
        feed=feed,
        bookingSummary=booking_summary,
        recentBookings=recent_bookings
    )
