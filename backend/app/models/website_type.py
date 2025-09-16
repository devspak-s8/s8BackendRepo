from pydantic import BaseModel, Field

class WebsiteTypeModel(BaseModel):
    name: str = Field(..., description="Website type, e.g., portfolio, landing, ecommerce, blog")
    description: str = Field("", description="Optional description")
