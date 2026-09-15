"""E-Commerce domain – Composite MCP server (4 high-level tools).

Run standalone:  python -m mcp_granite.mcp_servers.ecommerce.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
)
from mcp_granite.mcp_servers.ecommerce._store import ECommerceStore

mcp = FastMCP("ecommerce-composite")
store = ECommerceStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def find_and_order(
    search_query: str,
    quantity: int,
    shipping_address: str,
    discount_code: str | None = None,
    category: str | None = None,
) -> dict:
    """Search for a product, check inventory, add to cart, apply discount, and place order.

    Args:
        search_query: Keyword to search for products.
        quantity: Number of items to order.
        shipping_address: Full shipping address for the order.
        discount_code: Optional discount code to apply (e.g. 'SAVE10').
        category: Optional category filter (electronics, clothing, books).
    """
    fault = await injector.maybe_raise("find_and_order")

    # Step 1: Search products
    products = store.search_products(search_query, category)
    if not products:
        return {"error": f"No products found for '{search_query}'."}

    product = products[0]

    # Step 2: Check inventory
    inv = store.check_inventory(product.product_id)
    if not inv or not inv.get("in_stock") or inv["inventory"] < quantity:
        return {"error": f"Insufficient inventory for '{product.name}'."}

    # Step 3: Add to cart
    cart = store.add_to_cart(None, product.product_id, quantity)
    if not cart:
        return {"error": f"Could not add '{product.name}' to cart."}

    # Step 4: Apply discount (if provided)
    discount_info = None
    if discount_code:
        discount_info = store.apply_discount(cart.cart_id, discount_code)
        if discount_info and "error" in discount_info:
            discount_info = None

    # Step 5: Place order
    order = store.place_order(cart.cart_id, shipping_address, discount_code)
    if not order:
        return {"error": "Could not place order."}

    result = {
        "order_id": order.order_id,
        "product": product.model_dump(),
        "quantity": quantity,
        "subtotal": order.subtotal,
        "discount": order.discount,
        "shipping_cost": order.shipping_cost,
        "total": order.total,
        "shipping_address": shipping_address,
        "status": order.status,
        "discount_applied": discount_info,
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("product", None)
        result.pop("discount_applied", None)
    elif fault == FaultType.CONTRADICTORY:
        result["total"] = round(result["total"] * 0.1, 2)

    return result


@mcp.tool()
async def manage_order(
    order_id: str,
    action: str,
    new_address: str | None = None,
) -> dict:
    """Manage an existing order (update shipping address or cancel).

    Args:
        order_id: The order ID to manage.
        action: Action to take — 'update_shipping' or 'cancel'.
        new_address: New shipping address (required for 'update_shipping').
    """
    fault = await injector.maybe_raise("manage_order")

    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}

    if action == "update_shipping":
        if not new_address:
            return {"error": "New address is required for 'update_shipping' action."}
        result = store.update_shipping_address(order_id, new_address)
        if not result:
            return {"error": f"Could not update shipping for order '{order_id}'."}
        if "error" in result:
            return result
        result["action"] = "update_shipping"
        if fault == FaultType.PARTIAL_RESPONSE:
            result.pop("shipping_address", None)
        return result

    if action == "cancel":
        if order.status not in ("confirmed",):
            return {"error": f"Cannot cancel order with status '{order.status}'."}
        order.status = "cancelled"
        # Restore inventory
        for item in order.items:
            product = store.products.get(item.product_id)
            if product:
                product.inventory += item.quantity
        result = {
            "order_id": order_id,
            "action": "cancelled",
            "status": "cancelled",
            "refund_total": order.total,
        }
        if fault == FaultType.CONTRADICTORY:
            result["status"] = "processing"
        return result

    return {"error": f"Unknown action '{action}'."}


@mcp.tool()
async def process_return(
    order_id: str,
    product_id: str,
    reason: str,
) -> dict:
    """Initiate a return for a product in an order.

    Args:
        order_id: The order ID containing the product.
        product_id: The product ID to return.
        reason: Reason for the return.
    """
    fault = await injector.maybe_raise("process_return")

    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}

    result = store.initiate_return(order_id, product_id, reason)
    if not result:
        return {"error": f"Could not initiate return for order '{order_id}'."}
    if "error" in result:
        return result

    # Enrich with product details
    product = store.get_product(product_id)
    if product:
        result["product_name"] = product.name
        result["product_category"] = product.category

    result["order_status"] = store.get_order(order_id).status if store.get_order(order_id) else "unknown"

    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("product_name", None)
        result.pop("product_category", None)
    elif fault == FaultType.CONTRADICTORY:
        result["refund_amount"] = round(result.get("refund_amount", 0) * 0.1, 2)

    return result


@mcp.tool()
async def get_order_summary(order_id: str) -> dict:
    """Get a complete order summary with product details, shipping, and payment info.

    Args:
        order_id: The order ID to summarize.
    """
    fault = await injector.maybe_raise("get_order_summary")

    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}

    # Enrich items with full product details
    enriched_items = []
    for item in order.items:
        product = store.get_product(item.product_id)
        enriched = item.model_dump()
        if product:
            enriched["product_name"] = product.name
            enriched["product_category"] = product.category
            enriched["product_rating"] = product.rating
        enriched_items.append(enriched)

    summary: dict = {
        "order_id": order.order_id,
        "status": order.status,
        "items": enriched_items,
        "subtotal": order.subtotal,
        "discount": order.discount,
        "discount_code": order.discount_code,
        "shipping_cost": order.shipping_cost,
        "total": order.total,
        "shipping_address": order.shipping_address,
        "payment_info": {
            "method": "credit_card",
            "status": "charged" if order.status != "cancelled" else "refunded",
        },
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        summary.pop("items", None)
        summary.pop("payment_info", None)
    elif fault == FaultType.CONTRADICTORY:
        summary["status"] = "processing"

    return summary


if __name__ == "__main__":
    mcp.run(transport="stdio")
