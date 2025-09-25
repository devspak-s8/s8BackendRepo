# schemas/dashboard.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime
class DashboardOverview(BaseModel):
    user: Dict[str, Any]
    bookings_summary: Dict[str, int]
    notifications: Optional[int] = 0
    analytics: Dict[str, int]
    recent_bookings: List[Dict[str, Any]]
    recent_templates: List[Dict[str, Any]]
    leaderboard: List[Dict[str, Any]]
    active_projects: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]



# ------------------------
# Feed (Projects)
# ------------------------
class ProjectFeedItem(BaseModel):
    projectId: str
    title: str
    summary: str                  # Shortened description for card
    techStack: List[str]
    serviceType: Optional[str] = None
    postedAt: datetime
    developer: Optional[dict] = None  # Nested dev info (name, rating, location, rate)

class FeedPagination(BaseModel):
    nextCursor: Optional[str] = None
    hasMore: bool


class FeedResponse(BaseModel):
    projects: List[ProjectFeedItem]
    pagination: FeedPagination


# ------------------------
# Booking Summary
# ------------------------
class BookingSummary(BaseModel):
    totalBookings: int
    activeBookings: int
    completedBookings: int


# ------------------------
# Recent Bookings
# ------------------------
class RecentBooking(BaseModel):
    bookingId: str
    devName: str
    status: str  # Active, Completed, Pending, etc.
    startDate: datetime
    endDate: Optional[datetime] = None


# ------------------------
# Dashboard Response Wrapper
# ------------------------
class ClientDashboardResponse(BaseModel):
    feed: FeedResponse
    bookingSummary: BookingSummary
    recentBookings: List[RecentBooking]
