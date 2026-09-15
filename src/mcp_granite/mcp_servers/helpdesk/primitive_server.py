"""Helpdesk domain – Primitive MCP server (8 fine-grained tools).

Run standalone:  python -m mcp_granite.mcp_servers.helpdesk.primitive_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_granite.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
    truncate_response,
)
from mcp_granite.mcp_servers.helpdesk._store import HelpdeskStore

mcp = FastMCP("helpdesk-primitive")
store = HelpdeskStore()
injector = FaultInjector(FaultConfig.from_env())


# ── helpers ──────────────────────────────────────────────────────────────────

def _apply_fault(results: list[dict], fault: FaultType | None) -> list[dict]:
    if fault == FaultType.PARTIAL_RESPONSE:
        return truncate_response(results)
    return results


# ── tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def lookup_user(user_id: str) -> dict:
    """Look up an employee / IT user by their user ID."""
    fault = await injector.maybe_raise("lookup_user")
    user = store.lookup_user(user_id)
    if not user:
        return {"error": f"User '{user_id}' not found."}
    result = user.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("department", None)
        result.pop("role", None)
    return result


@mcp.tool()
async def check_system_status(system_name: str | None = None) -> list[dict]:
    """Check the operational status of IT systems. Omit system_name to list all."""
    fault = await injector.maybe_raise("check_system_status")
    systems = store.check_system_status(system_name)
    results = [s.model_dump() for s in systems]
    return _apply_fault(results, fault)


@mcp.tool()
async def search_knowledge_base(query: str, max_results: int = 5) -> list[dict]:
    """Search the IT knowledge base for articles matching a query."""
    fault = await injector.maybe_raise("search_knowledge_base")
    articles = store.search_knowledge_base(query, max_results)
    results = [a.model_dump() for a in articles]
    return _apply_fault(results, fault)


@mcp.tool()
async def diagnose_issue(user_id: str, issue_description: str) -> dict:
    """Run a basic diagnostic based on the user's issue description.

    Checks relevant system statuses and searches the knowledge base for matching articles.
    """
    fault = await injector.maybe_raise("diagnose_issue")

    # Keyword-based system check
    keywords_to_systems = {
        "email": "Email",
        "vpn": "VPN",
        "crm": "CRM",
        "wiki": "Wiki",
    }
    affected_systems = []
    desc_lower = issue_description.lower()
    for keyword, system_name in keywords_to_systems.items():
        if keyword in desc_lower:
            matches = store.check_system_status(system_name)
            affected_systems.extend([s.model_dump() for s in matches])

    # Search knowledge base for relevant articles
    articles = store.search_knowledge_base(issue_description, max_results=3)

    diagnosis = {
        "user_id": user_id,
        "issue_description": issue_description,
        "affected_systems": affected_systems,
        "suggested_articles": [a.model_dump() for a in articles],
        "recommendation": "Review the suggested articles. If the issue persists, create a support ticket.",
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        diagnosis.pop("suggested_articles", None)
    elif fault == FaultType.CONTRADICTORY:
        # Report all systems as operational even if they are not
        for sys in diagnosis.get("affected_systems", []):
            sys["status"] = "operational"

    return diagnosis


@mcp.tool()
async def create_ticket(
    user_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> dict:
    """Create a new IT support ticket for a user."""
    fault = await injector.maybe_raise("create_ticket")
    ticket = store.create_ticket(user_id, subject, description, priority)
    if not ticket:
        return {"error": f"Could not create ticket. User '{user_id}' not found."}
    result = ticket.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("history", None)
    return result


@mcp.tool()
async def update_ticket(
    ticket_id: str,
    status: str | None = None,
    note: str | None = None,
    priority: str | None = None,
) -> dict:
    """Update an existing support ticket's status, priority, or add a note."""
    fault = await injector.maybe_raise("update_ticket")
    ticket = store.update_ticket(ticket_id, status=status, note=note, priority=priority)
    if not ticket:
        return {"error": f"Ticket '{ticket_id}' not found."}
    result = ticket.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "open"  # lie about status
    return result


@mcp.tool()
async def escalate_ticket(ticket_id: str, reason: str) -> dict:
    """Escalate a support ticket to L2 Support."""
    fault = await injector.maybe_raise("escalate_ticket")
    ticket = store.escalate_ticket(ticket_id, reason)
    if not ticket:
        return {"error": f"Ticket '{ticket_id}' not found."}
    result = ticket.model_dump()
    if fault == FaultType.PARTIAL_RESPONSE:
        result.pop("history", None)
    return result


@mcp.tool()
async def get_ticket_status(ticket_id: str) -> dict:
    """Get the current status and details of a support ticket."""
    fault = await injector.maybe_raise("get_ticket_status")
    ticket = store.get_ticket(ticket_id)
    if not ticket:
        return {"error": f"Ticket '{ticket_id}' not found."}
    result = ticket.model_dump()
    if fault == FaultType.CONTRADICTORY:
        result["status"] = "resolved"  # lie about status
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
