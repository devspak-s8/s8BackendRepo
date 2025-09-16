from pydantic import BaseModel, Field

class PageTypeModel(BaseModel):
    name: str = Field(..., description="Name of the page type, e.g., single, double, custom")
    description: str = Field("", description="Optional description")
    max_pages: int = Field(1, description="Maximum pages allowed for this type")
