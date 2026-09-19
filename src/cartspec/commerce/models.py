from pydantic import BaseModel


class Product(BaseModel):
    id: str
    name: str
    category: str


class Merchant(BaseModel):
    id: str
    name: str


class Offer(BaseModel):
    id: str
    product_id: str
    merchant_id: str
    price: float
    currency: str


class Inventory(BaseModel):
    offer_id: str
    quantity: int


class CartItem(BaseModel):
    offer_id: str
    quantity: int


class Cart(BaseModel):
    id: str
    items: list[CartItem]


class Order(BaseModel):
    id: str
    offer_id: str
    quantity: int
    unit_price: float
    currency: str
    total_price: float
    status: str
