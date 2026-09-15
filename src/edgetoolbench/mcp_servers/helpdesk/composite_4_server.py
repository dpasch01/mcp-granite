"""Helpdesk domain – Composite MCP server (3 high-level tools).

Run standalone:  python -m edgetoolbench.mcp_servers.helpdesk.composite_4_server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from edgetoolbench.mcp_servers._base import (
    FaultConfig,
    FaultInjector,
    FaultType,
)
from edgetoolbench.mcp_servers.helpdesk._store import HelpdeskStore

mcp = FastMCP("helpdesk-composite")
store = HelpdeskStore()
injector = FaultInjector(FaultConfig.from_env())


@mcp.tool()
async def diagnose_and_resolve(user_id: str, issue_description: str) -> dict:
    """Diagnose an IT issue and create a support ticket in a single operation.

    Internally looks up the user, checks relevant system statuses, searches the
    knowledge base for matching articles, and creates a ticket with the diagnosis.

    Args:
        user_id: The employee's user ID (e.g. 'USR001').
        issue_description: Free-text description of the issue the user is experiencing.
    """
    fault = await injector.maybe_raise("diagnose_and_resolve")

    # Step 1 – Look up user
    user = store.lookup_user(user_id)
    if not user:
        return {"error": f"User '{user_id}' not found."}

    # Step 2 – Check relevant system statuses
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

    # Step 3 – Search knowledge base
    articles = store.search_knowledge_base(issue_description, max_results=3)
    related_article_ids = [a.article_id for a in articles]

    # Step 4 – Determine priority based on system status
    priority = "medium"
    for sys in affected_systems:
        if sys["status"] == "down":
            priority = "critical"
            break
        if sys["status"] == "degraded":
            priority = "high"

    # Step 5 – Create ticket
    ticket = store.create_ticket(
        user_id=user_id,
        subject=f"Auto: {issue_description[:80]}",
        description=issue_description,
        priority=priority,
        related_articles=related_article_ids,
    )

    result = {
        "diagnosis": {
            "user": user.model_dump(),
            "affected_systems": affected_systems,
            "suggested_articles": [a.model_dump() for a in articles],
            "auto_priority": priority,
        },
        "ticket": ticket.model_dump() if ticket else None,
        "recommendation": (
            "Review the suggested knowledge base articles. "
            "A support ticket has been automatically created."
        ),
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        result["diagnosis"].pop("suggested_articles", None)
        result["diagnosis"].pop("affected_systems", None)
    elif fault == FaultType.CONTRADICTORY:
        for sys in result["diagnosis"].get("affected_systems", []):
            sys["status"] = "operational"
        if result.get("ticket"):
            result["ticket"]["priority"] = "low"

    return result


@mcp.tool()
async def manage_ticket(
    ticket_id: str,
    action: str,
    note: str | None = None,
    reason: str | None = None,
    priority: str | None = None,
) -> dict:
    """Manage a support ticket: update, escalate, or close it.

    Args:
        ticket_id: The ticket ID (e.g. 'TK001').
        action: One of 'update', 'escalate', or 'close'.
        note: Optional note to add to the ticket history.
        reason: Required when action is 'escalate' — the reason for escalation.
        priority: Optional new priority level (low/medium/high/critical).
    """
    fault = await injector.maybe_raise("manage_ticket")

    ticket = store.get_ticket(ticket_id)
    if not ticket:
        return {"error": f"Ticket '{ticket_id}' not found."}

    if action == "escalate":
        escalation_reason = reason or "Escalated via manage_ticket."
        updated = store.escalate_ticket(ticket_id, escalation_reason)
        if not updated:
            return {"error": f"Failed to escalate ticket '{ticket_id}'."}
        result = {
            "ticket_id": ticket_id,
            "action": "escalated",
            "ticket": updated.model_dump(),
        }

    elif action == "close":
        updated = store.update_ticket(
            ticket_id, status="closed", note=note or "Ticket closed.",
        )
        if not updated:
            return {"error": f"Failed to close ticket '{ticket_id}'."}
        result = {
            "ticket_id": ticket_id,
            "action": "closed",
            "ticket": updated.model_dump(),
        }

    elif action == "update":
        updated = store.update_ticket(
            ticket_id, status=None, note=note, priority=priority,
        )
        if not updated:
            return {"error": f"Failed to update ticket '{ticket_id}'."}
        result = {
            "ticket_id": ticket_id,
            "action": "updated",
            "ticket": updated.model_dump(),
        }

    else:
        return {"error": f"Unknown action '{action}'. Use 'update', 'escalate', or 'close'."}

    if fault == FaultType.PARTIAL_RESPONSE:
        result.get("ticket", {}).pop("history", None)
    elif fault == FaultType.CONTRADICTORY:
        if "ticket" in result:
            result["ticket"]["status"] = "open"

    return result


@mcp.tool()
async def get_case_summary(ticket_id: str) -> dict:
    """Get a comprehensive case summary including user info, ticket history, and KB references.

    Args:
        ticket_id: The ticket ID (e.g. 'TK001').
    """
    fault = await injector.maybe_raise("get_case_summary")

    ticket = store.get_ticket(ticket_id)
    if not ticket:
        return {"error": f"Ticket '{ticket_id}' not found."}

    # Enrich with user data
    user = store.lookup_user(ticket.user_id)

    # Enrich with related KB articles
    related_articles = []
    for aid in ticket.related_articles:
        for article in store.articles.values():
            if article.article_id == aid:
                related_articles.append(article.model_dump())

    # Check status of potentially affected systems
    system_statuses = [s.model_dump() for s in store.check_system_status()]

    summary: dict = {
        "ticket": ticket.model_dump(),
        "user": user.model_dump() if user else None,
        "related_articles": related_articles,
        "system_statuses": system_statuses,
        "history_count": len(ticket.history),
    }

    if fault == FaultType.PARTIAL_RESPONSE:
        summary.pop("related_articles", None)
        summary.pop("system_statuses", None)
    elif fault == FaultType.CONTRADICTORY:
        summary["ticket"]["status"] = "resolved"

    return summary


if __name__ == "__main__":
    mcp.run(transport="stdio")
