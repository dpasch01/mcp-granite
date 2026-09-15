"""In-memory data store for the E-Commerce domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.ecommerce._domain import (
    Cart,
    CartItem,
    DiscountCode,
    Order,
    Product,
)


class ECommerceStore:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.carts: dict[str, Cart] = {}
        self.orders: dict[str, Order] = {}
        self.discount_codes: dict[str, DiscountCode] = {}
        self._next_order = 2  # 1 is pre-seeded
        self._next_cart = 2   # 1 is pre-seeded
        self._seed_data()

    def _seed_data(self) -> None:
        product_data = [
            ("Wireless Bluetooth Headphones", "electronics", 79.99, 150, "Over-ear noise-cancelling headphones with 30h battery", 4.5),
            ("USB-C Charging Cable 6ft", "electronics", 12.99, 500, "Braided nylon USB-C to USB-C fast charging cable", 4.2),
            ("Mechanical Keyboard", "electronics", 129.99, 75, "RGB backlit mechanical keyboard with Cherry MX switches", 4.7),
            ("Cotton Crew T-Shirt", "clothing", 24.99, 300, "100% organic cotton crew-neck t-shirt, multiple colors", 4.0),
            ("Slim Fit Jeans", "clothing", 49.99, 200, "Stretch denim slim fit jeans in classic indigo wash", 4.3),
            ("Running Sneakers", "clothing", 89.99, 120, "Lightweight breathable mesh running shoes with cushioned sole", 4.6),
            ("The Art of Programming", "books", 39.99, 60, "Comprehensive guide to software design patterns and best practices", 4.8),
            ("Data Science Handbook", "books", 34.99, 45, "Practical handbook covering statistics, ML, and data visualization", 4.4),
        ]
        for i, (name, category, price, inventory, desc, rating) in enumerate(product_data, 1):
            pid = generate_id("PR", i)
            self.products[pid] = Product(
                product_id=pid, name=name, category=category,
                price=price, inventory=inventory, description=desc, rating=rating,
            )

        discount_data = [
            ("SAVE10", "percentage", 10.0),
            ("SAVE20", "percentage", 20.0),
            ("FREESHIP", "free_shipping", 0.0),
        ]
        for code, dtype, value in discount_data:
            self.discount_codes[code] = DiscountCode(
                code=code, discount_type=dtype, value=value,
            )

        # Pre-existing cart with 1 item (Wireless Bluetooth Headphones)
        cart_id = generate_id("CT", 1)
        self.carts[cart_id] = Cart(
            cart_id=cart_id,
            items=[CartItem(product_id="PR001", quantity=1, unit_price=79.99)],
            total=79.99,
        )

        # Pre-existing order (delivered)
        order_id = generate_id("OR", 1)
        self.orders[order_id] = Order(
            order_id=order_id,
            cart_id=cart_id,
            items=[CartItem(product_id="PR001", quantity=1, unit_price=79.99)],
            subtotal=79.99,
            discount=0.0,
            shipping_cost=5.99,
            total=85.98,
            shipping_address="123 Main St, Springfield, IL 62701",
            status="delivered",
            discount_code=None,
        )

    # ----- Query methods -----

    def search_products(
        self, query: str, category: str | None = None, max_results: int = 5
    ) -> list[Product]:
        query_lower = query.lower()
        matches = [
            p for p in self.products.values()
            if query_lower in p.name.lower() or query_lower in p.description.lower()
        ]
        if category:
            matches = [p for p in matches if p.category.lower() == category.lower()]
        matches.sort(key=lambda p: -p.rating)
        return matches[:max_results]

    def get_product(self, product_id: str) -> Product | None:
        return self.products.get(product_id)

    def check_inventory(self, product_id: str) -> dict | None:
        product = self.products.get(product_id)
        if not product:
            return None
        return {
            "product_id": product_id,
            "name": product.name,
            "inventory": product.inventory,
            "in_stock": product.inventory > 0,
        }

    def get_cart(self, cart_id: str) -> Cart | None:
        return self.carts.get(cart_id)

    def get_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    # ----- Mutation methods -----

    def add_to_cart(self, cart_id: str | None, product_id: str, quantity: int = 1) -> Cart | None:
        product = self.products.get(product_id)
        if not product or product.inventory < quantity:
            return None

        if cart_id and cart_id in self.carts:
            cart = self.carts[cart_id]
        else:
            cart_id = generate_id("CT", self._next_cart)
            self._next_cart += 1
            cart = Cart(cart_id=cart_id, items=[], total=0.0)
            self.carts[cart_id] = cart

        # Check if product already in cart
        existing = next((item for item in cart.items if item.product_id == product_id), None)
        if existing:
            existing.quantity += quantity
        else:
            cart.items.append(CartItem(
                product_id=product_id, quantity=quantity, unit_price=product.price,
            ))

        cart.total = round(sum(item.unit_price * item.quantity for item in cart.items), 2)
        return cart

    def remove_from_cart(self, cart_id: str, product_id: str) -> Cart | None:
        cart = self.carts.get(cart_id)
        if not cart:
            return None
        cart.items = [item for item in cart.items if item.product_id != product_id]
        cart.total = round(sum(item.unit_price * item.quantity for item in cart.items), 2)
        return cart

    def apply_discount(self, cart_id: str, code: str) -> dict | None:
        cart = self.carts.get(cart_id)
        if not cart:
            return None
        discount = self.discount_codes.get(code.upper())
        if not discount:
            return {"error": f"Invalid discount code '{code}'."}

        if discount.discount_type == "percentage":
            discount_amount = round(cart.total * discount.value / 100.0, 2)
            return {
                "cart_id": cart_id,
                "code": discount.code,
                "discount_type": "percentage",
                "discount_amount": discount_amount,
                "new_total": round(cart.total - discount_amount, 2),
            }
        elif discount.discount_type == "free_shipping":
            return {
                "cart_id": cart_id,
                "code": discount.code,
                "discount_type": "free_shipping",
                "discount_amount": 5.99,
                "new_total": cart.total,
            }
        return None

    def place_order(
        self, cart_id: str, shipping_address: str, discount_code: str | None = None
    ) -> Order | None:
        cart = self.carts.get(cart_id)
        if not cart or not cart.items:
            return None

        # Validate inventory and deduct
        for item in cart.items:
            product = self.products.get(item.product_id)
            if not product or product.inventory < item.quantity:
                return None

        for item in cart.items:
            product = self.products[item.product_id]
            product.inventory -= item.quantity

        subtotal = cart.total
        discount_amount = 0.0
        shipping_cost = 5.99

        if discount_code:
            dc = self.discount_codes.get(discount_code.upper())
            if dc:
                if dc.discount_type == "percentage":
                    discount_amount = round(subtotal * dc.value / 100.0, 2)
                elif dc.discount_type == "free_shipping":
                    shipping_cost = 0.0

        total = round(subtotal - discount_amount + shipping_cost, 2)

        order_id = generate_id("OR", self._next_order)
        self._next_order += 1
        order = Order(
            order_id=order_id,
            cart_id=cart_id,
            items=list(cart.items),
            subtotal=subtotal,
            discount=discount_amount,
            shipping_cost=shipping_cost,
            total=total,
            shipping_address=shipping_address,
            status="confirmed",
            discount_code=discount_code,
        )
        self.orders[order_id] = order
        return order

    def initiate_return(self, order_id: str, product_id: str, reason: str) -> dict | None:
        order = self.orders.get(order_id)
        if not order:
            return None
        if order.status not in ("confirmed", "shipped", "delivered"):
            return {"error": f"Cannot initiate return for order with status '{order.status}'."}

        matching_item = next(
            (item for item in order.items if item.product_id == product_id), None,
        )
        if not matching_item:
            return {"error": f"Product '{product_id}' not found in order '{order_id}'."}

        order.status = "return_initiated"
        # Restore inventory
        product = self.products.get(product_id)
        if product:
            product.inventory += matching_item.quantity

        return {
            "order_id": order_id,
            "product_id": product_id,
            "reason": reason,
            "refund_amount": round(matching_item.unit_price * matching_item.quantity, 2),
            "status": "return_initiated",
        }

    def update_shipping_address(self, order_id: str, new_address: str) -> dict | None:
        order = self.orders.get(order_id)
        if not order:
            return None
        if order.status not in ("confirmed",):
            return {"error": f"Cannot update shipping for order with status '{order.status}'."}
        order.shipping_address = new_address
        return {
            "order_id": order_id,
            "shipping_address": new_address,
            "status": order.status,
        }
