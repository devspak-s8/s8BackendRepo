from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class VariantModel(BaseModel):
    name: str = Field(..., description="Variant name, e.g., MinimalHero")
    required_props: List[str] = Field([], description="Props that user must fill, e.g., title, image, description")

class ComponentModel(BaseModel):
    name: str = Field(..., description="Component name, e.g., HeroSection")
    variants: List[VariantModel] = Field(..., description="Available variants for this component")
