"""
Pydantic schemas for shopping list endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID

from voice_assistant.domain.value_objects.priority import Priority


class ShoppingItemCreateRequest(BaseModel):
    """Request to create a shopping list item"""
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    quantity: int = Field(1, ge=1, le=9999, description="Item quantity")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measurement (kg, pcs, etc.)")
    priority: str = Field("normal", description="Item priority (low, normal, high)")

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority value"""
        valid_priorities = {'low', 'normal', 'high'}
        if v.lower() not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v.lower()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean item name"""
        cleaned = v.strip()
        if len(cleaned) < 1:
            raise ValueError("Item name cannot be empty")
        return cleaned


class ShoppingItemUpdateRequest(BaseModel):
    """Request to update a shopping list item"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Item name")
    quantity: Optional[int] = Field(None, ge=1, le=9999, description="Item quantity")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measurement")
    priority: Optional[str] = Field(None, description="Item priority (low, normal, high)")
    purchased: Optional[bool] = Field(None, description="Whether item is purchased")

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        """Validate priority value"""
        if v is None:
            return v
        valid_priorities = {'low', 'normal', 'high'}
        if v.lower() not in valid_priorities:
            raise ValueError(f"Priority must be one of: {valid_priorities}")
        return v.lower()


class ShoppingItemResponse(BaseModel):
    """Shopping list item response"""
    id: str = Field(..., description="Item ID")
    name: str = Field(..., description="Item name")
    quantity: int = Field(..., description="Item quantity")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    priority: str = Field(..., description="Item priority")
    added_at: datetime = Field(..., description="When item was added")
    purchased: bool = Field(False, description="Whether item is purchased")

    class Config:
        from_attributes = True


class ShoppingListResponse(BaseModel):
    """Shopping list response"""
    session_id: str = Field(..., description="Session ID")
    items: list[ShoppingItemResponse] = Field(default_factory=list, description="List of items")
    total_count: int = Field(0, ge=0, description="Total number of items")
    pending_count: int = Field(0, ge=0, description="Number of pending items")
    purchased_count: int = Field(0, ge=0, description="Number of purchased items")


class ShoppingItemDeleteResponse(BaseModel):
    """Shopping item deletion response"""
    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Result message")
    deleted_item_id: Optional[str] = Field(None, description="ID of deleted item")