"""Domain models for the E-Commerce mock."""

from __future__ import annotations

from pydantic import BaseModel


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    inventory: int
    description: str
    rating: float


class CartItem(BaseModel):
    product_id: str
    quantity: int
    unit_price: float


class Cart(BaseModel):
    cart_id: str
    items: list[CartItem]
    total: float


class Order(BaseModel):
    order_id: str
    cart_id: str
    items: list[CartItem]
    subtotal: float
    discount: float
    shipping_cost: float
    total: float
    shipping_address: str
    status: str  # "confirmed", "shipped", "delivered", "cancelled", "return_initiated"
    discount_code: str | None


class DiscountCode(BaseModel):
    code: str
    discount_type: str  # "percentage" or "free_shipping"
    value: float  # percentage value or 0 for free_shipping
