from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import uuid

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
    tech_stack: List[str]  # Preferred tech stack for the project
    profile_picture: Optional[str] = None
    professional_links: Optional[List[HttpUrl]] = None  # Optional client links

# ------------------------
# Developer Project Schema
# ------------------------

class ProjectSchema(BaseModel):
    id: Optional[str] = None  # Unique ID for project
    name: str
    description: str
    github: HttpUrl
    live_demo: Optional[HttpUrl] = None
    tech_stack: List[str]

    def assign_id(self):
        if not self.id:
            self.id = str(uuid.uuid4())
# ------------------------
# Developer Profile Schema
# ------------------------
class DevProfileSchema(BaseModel):
    dev_type: str  # Frontend, Backend, Full-stack, Mobile, DevOps
    tech_stack: List[str]
    projects: List[ProjectSchema]
    bio: str  # 0-500 chars
    profile_picture: Optional[str] = None
    professional_links: Optional[List[HttpUrl]] = None  # GitHub, LinkedIn, portfolio site
