from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uuid
from datetime import datetime

# ------------------------
# Client Profile Schema
# ------------------------
class ClientProfileSchema(BaseModel):
    name: str
    company: Optional[str] = None
    location: str
    industry: str
    budget_min: int
    budget_max: int
    preferred_services: List[str]              # What services they are looking for
    profile_picture: Optional[str] = None
    links: Optional[List[HttpUrl]] = None      # Optional external links

# ------------------------
# Developer Project Schema
# ------------------------
class ProjectSchema(BaseModel):
    id: Optional[str] = None                   # Unique ID for project
    name: str
    description: str
    github: HttpUrl
    live_demo: Optional[HttpUrl] = None
    tech_stack: List[str]
    serviceType: Optional[str] = None          # e.g., "Full-stack Development"
    created_at: Optional[datetime] = None      # For ordering in feeds

    def assign_id(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
            
# ------------------------
# Developer Profile Schema
# ------------------------
class DevProfileSchema(BaseModel):
    dev_type: str                              # Frontend, Backend, Full-stack, Mobile, DevOps
    tech_stack: List[str]                      # Developer’s actual stack
    services: List[str]                        # Services they provide (matches client preferences)
    projects: List[ProjectSchema]
    bio: str                                   # 0-500 chars
    profile_picture: Optional[str] = None
    links: Optional[List[HttpUrl]] = None      # GitHub, LinkedIn, portfolio site
