import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

# App
app = FastAPI(title="Cafeteria Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database helpers
from database import db, create_document, get_documents

# Schemas
from schemas import Staff, Menuitem, Order, Inventory

# Utility

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

# Basic health
@app.get("/")
def read_root():
    return {"message": "Cafeteria Management Backend Running"}

@app.get("/test")
def test_database():
    status = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            status["database"] = "✅ Available"
            status["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            status["database_name"] = getattr(db, 'name', None) or "✅ Connected"
            status["connection_status"] = "Connected"
            try:
                status["collections"] = db.list_collection_names()
                status["database"] = "✅ Connected & Working"
            except Exception as e:
                status["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            status["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        status["database"] = f"❌ Error: {str(e)[:80]}"
    return status

# Public menu endpoints
@app.get("/api/menu")
def list_menu():
    docs = get_documents("menuitem")
    # convert ObjectId to str
    for d in docs:
        d["_id"] = str(d["_id"]) 
    return docs

class MenuCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    available: bool = True

@app.post("/api/menu", status_code=201)
def create_menu_item(payload: MenuCreate):
    item = Menuitem(**payload.model_dump())
    new_id = create_document("menuitem", item)
    return {"id": new_id}

# Orders
class OrderItem(BaseModel):
    menu_item_id: str
    quantity: int

class OrderCreate(BaseModel):
    staff_id: Optional[str] = None
    items: List[OrderItem]
    note: Optional[str] = None

@app.post("/api/orders", status_code=201)
def create_order(payload: OrderCreate):
    # compute pricing from menu
    ids = [oid(i.menu_item_id) for i in payload.items]
    menu_map = {str(d["_id"]): d for d in db["menuitem"].find({"_id": {"$in": ids}})}
    subtotal = 0.0
    item_lines = []
    for it in payload.items:
        m = menu_map.get(it.menu_item_id)
        if not m:
            raise HTTPException(status_code=400, detail=f"Menu item not found: {it.menu_item_id}")
        line_total = float(m.get("price", 0)) * int(it.quantity)
        subtotal += line_total
        item_lines.append({"menu_item_id": it.menu_item_id, "quantity": it.quantity, "price": float(m.get("price", 0)), "title": m.get("title")})
    tax = round(subtotal * 0.07, 2)
    total = round(subtotal + tax, 2)
    order_doc = Order(
        staff_id=payload.staff_id,
        items=item_lines,
        subtotal=round(subtotal, 2),
        tax=tax,
        total=total,
        status="open",
        note=payload.note,
    )
    new_id = create_document("order", order_doc)
    return {"id": new_id, "subtotal": order_doc.subtotal, "tax": order_doc.tax, "total": order_doc.total}

@app.get("/api/orders")
def list_orders():
    docs = get_documents("order")
    for d in docs:
        d["_id"] = str(d["_id"]) 
    return docs

# Inventory simple endpoints
class InventoryUpsert(BaseModel):
    sku: str
    quantity: float
    unit: str = "unit"
    reorder_level: Optional[float] = None

@app.get("/api/inventory")
def list_inventory():
    docs = get_documents("inventory")
    for d in docs:
        d["_id"] = str(d["_id"]) 
    return docs

@app.post("/api/inventory", status_code=201)
def upsert_inventory(item: InventoryUpsert):
    # upsert by sku
    existing = db["inventory"].find_one({"sku": item.sku})
    if existing:
        db["inventory"].update_one({"_id": existing["_id"]}, {"$set": {"quantity": item.quantity, "unit": item.unit, "reorder_level": item.reorder_level}})
        return {"id": str(existing["_id"]) }
    doc = Inventory(**item.model_dump())
    new_id = create_document("inventory", doc)
    return {"id": new_id}

# Staff simple endpoints (demo PIN auth)
class StaffCreate(BaseModel):
    name: str
    role: str
    pin: str

@app.post("/api/staff", status_code=201)
def create_staff(s: StaffCreate):
    staff_doc = Staff(**s.model_dump())
    new_id = create_document("staff", staff_doc)
    return {"id": new_id}

class StaffLogin(BaseModel):
    pin: str

@app.post("/api/auth/login")
def login(staff: StaffLogin):
    doc = db["staff"].find_one({"pin": staff.pin, "is_active": True})
    if not doc:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {"id": str(doc["_id"]), "name": doc.get("name"), "role": doc.get("role")}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
