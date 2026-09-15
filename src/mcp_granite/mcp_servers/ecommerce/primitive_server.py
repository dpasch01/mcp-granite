"""E-Commerce domain – Primitive MCP server (10 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.ecommerce.primitive_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    corrupt_numeric_field,
    truncate_response,
)
from mcp_granite.mcp_servers.ecommerce._store import ECommerceStore

mcp = FastMCP("ecommerce-primitive")
store = ECommerceStore()
injector = FaultInjector(FaultConfig.from_env())


# ── helpers ──────────────────────────────────────────────────────────────────

def _apply_fault(results: list[dict], fault: FaultType | None) -> list[dict]:
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    if fault == FaultType.CONTRADICTORY:
        return [corrupt_numeric_field(r, "price") for r in results]
    return results


# ── tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_products(
    query: str, category: str | None = None, max_results: int = 5
) -> list[dict]:
    """Search for products by keyword and optional category."""
    fault = await injector.maybe_raise("search_products")
    products = store.search_products(query, category, max_results)
    results = [p.model_dump() for p in products]
    return _apply_fault(results, fault)


@mcp.tool()
async def get_product_details(product_id: str) -> dict:
    """Get detailed information about a specific product."""
    fault = await injector.maybe_raise("get_product_details")
    product = store.get_product(product_id)
    if not product:
        return {"error": f"Product '{product_id}' not found."}
    result = product.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "price")
    return result


@mcp.tool()
async def check_inventory(product_id: str) -> dict:
    """Check inventory availability for a specific product."""
    fault = await injector.maybe_raise("check_inventory")
    result = store.check_inventory(product_id)
    if not result:
        return {"error": f"Product '{product_id}' not found."}
    if fault == FaultType.CONTRADICTORY:
        result = {**result, "inventory": 0, "in_stock": False}
    return result


@mcp.tool()
async def add_to_cart(
    product_id: str, quantity: int = 1, cart_id: str | None = None
) -> dict:
    """Add a product to a shopping cart. Creates a new cart if cart_id is not provided."""
    fault = await injector.maybe_raise("add_to_cart")
    cart = store.add_to_cart(cart_id, product_id, quantity)
    if not cart:
        return {"error": f"Could not add product '{product_id}' to cart."}
    result = cart.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("items", None)
    return result


@mcp.tool()
async def remove_from_cart(cart_id: str, product_id: str) -> dict:
    """Remove a product from a shopping cart."""
    fault = await injector.maybe_raise("remove_from_cart")
    cart = store.remove_from_cart(cart_id, product_id)
    if not cart:
        return {"error": f"Cart '{cart_id}' not found."}
    result = cart.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("items", None)
    return result


@mcp.tool()
async def apply_discount(cart_id: str, code: str) -> dict:
    """Apply a discount code to a shopping cart."""
    fault = await injector.maybe_raise("apply_discount")
    result = store.apply_discount(cart_id, code)
    if not result:
        return {"error": f"Could not apply discount to cart '{cart_id}'."}
    if "error" in result:
        return result
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "discount_amount")
    return result


@mcp.tool()
async def place_order(
    cart_id: str, shipping_address: str, discount_code: str | None = None
) -> dict:
    """Place an order from a shopping cart."""
    fault = await injector.maybe_raise("place_order")
    order = store.place_order(cart_id, shipping_address, discount_code)
    if not order:
        return {"error": f"Could not place order for cart '{cart_id}'."}
    result = order.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("items", None)
    return result


@mcp.tool()
async def get_order_status(order_id: str) -> dict:
    """Get the current status of an order."""
    fault = await injector.maybe_raise("get_order_status")
    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}
    result = order.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "processing"
    return result


@mcp.tool()
async def initiate_return(order_id: str, product_id: str, reason: str) -> dict:
    """Initiate a return for a product in an order."""
    fault = await injector.maybe_raise("initiate_return")
    result = store.initiate_return(order_id, product_id, reason)
    if not result:
        return {"error": f"Order '{order_id}' not found."}
    if "error" in result:
        return result
    if fault == FaultType.CONTRADICTORY:
        result = corrupt_numeric_field(result, "refund_amount")
    return result


@mcp.tool()
async def update_shipping(order_id: str, new_address: str) -> dict:
    """Update the shipping address for an order."""
    await injector.maybe_raise("update_shipping")
    result = store.update_shipping_address(order_id, new_address)
    if not result:
        return {"error": f"Order '{order_id}' not found."}
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
