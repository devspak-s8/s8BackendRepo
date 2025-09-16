from pydantic import BaseModel, Field
from typing import List, Dict, Any

class PageComponentProps(BaseModel):
    component_name: str
    variant_name: str
    props: Dict[str, Any]

class GeneratedPageModel(BaseModel):
    page_name: str
    components: List[PageComponentProps]

class GeneratedWebsiteModel(BaseModel):
    user_id: str
    page_type: str
    website_type: str
    pages: List[GeneratedPageModel]
    created_at: str
