"""
Database Schemas for Cafeteria Management

Each Pydantic model maps to a MongoDB collection (lowercased model name).
"""

from pydantic import BaseModel, Field
from typing import List, Optional

class Staff(BaseModel):
    name: str = Field(..., description="Full name")
    role: str = Field(..., description="Role e.g., cashier, manager, chef")
    pin: str = Field(..., min_length=4, max_length=8, description="Login PIN (demo)")
    is_active: bool = Field(True, description="Active staff member")

class Menuitem(BaseModel):
    title: str = Field(..., description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: Optional[str] = Field(None, description="Category like Drinks, Mains, Snacks")
    available: bool = Field(True, description="Whether item is available")

class Order(BaseModel):
    staff_id: Optional[str] = Field(None, description="ID of staff who created the order")
    items: List[dict] = Field(..., description="List of {menu_item_id, quantity}")
    subtotal: float = Field(..., ge=0, description="Subtotal before tax/discount")
    tax: float = Field(0, ge=0, description="Tax amount")
    total: float = Field(..., ge=0, description="Grand total")
    status: str = Field("open", description="open, paid, cancelled")
    note: Optional[str] = None

class Inventory(BaseModel):
    sku: str = Field(..., description="Stock keeping unit / name")
    quantity: float = Field(..., description="Current quantity on hand")
    unit: str = Field("unit", description="unit of measure, e.g., unit, kg, L")
    reorder_level: Optional[float] = Field(None, description="Minimum desired quantity")

# The Flames database viewer uses GET /schema to read these
