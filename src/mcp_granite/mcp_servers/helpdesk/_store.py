"""In-memory data store for the Helpdesk domain with deterministic seed data."""

from __future__ import annotations

from mcp_granite.mcp_servers._data import generate_id
from mcp_granite.mcp_servers.helpdesk._domain import (
    KnowledgeBaseArticle,
    SystemStatus,
    Ticket,
    User,
)


class HelpdeskStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.systems: dict[str, SystemStatus] = {}
        self.articles: dict[str, KnowledgeBaseArticle] = {}
        self.tickets: dict[str, Ticket] = {}
        self._next_ticket = 3  # 2 pre-existing tickets
        self._seed_data()

    def _seed_data(self) -> None:
        # ── Users (5 employees needing IT support) ──────────────────────────
        user_data = [
            ("Alice Johnson", "alice.johnson@acme.com", "Engineering", "Software Engineer"),
            ("Bob Martinez", "bob.martinez@acme.com", "Sales", "Account Executive"),
            ("Carol Chen", "carol.chen@acme.com", "Finance", "Financial Analyst"),
            ("David Kim", "david.kim@acme.com", "Marketing", "Marketing Manager"),
            ("Eva Novak", "eva.novak@acme.com", "Human Resources", "HR Specialist"),
        ]
        for i, (name, email, dept, role) in enumerate(user_data, 1):
            uid = generate_id("USR", i)
            self.users[uid] = User(
                user_id=uid, name=name, email=email, department=dept, role=role,
            )

        # ── Systems (4 systems with statuses) ──────────────────────────────
        system_data = [
            ("Corporate Email", "operational", "2025-06-01T08:00:00Z", "All email services running normally."),
            ("VPN Gateway", "degraded", "2025-06-01T07:45:00Z", "Intermittent connectivity issues reported in EU region."),
            ("CRM Platform", "operational", "2025-06-01T08:00:00Z", "CRM fully operational."),
            ("Internal Wiki", "down", "2025-06-01T06:30:00Z", "Scheduled maintenance in progress. ETA for restoration: 10:00 UTC."),
        ]
        for i, (name, status, checked, msg) in enumerate(system_data, 1):
            sid = generate_id("SYS", i)
            self.systems[sid] = SystemStatus(
                system_id=sid, name=name, status=status,
                last_checked=checked, message=msg,
            )

        # ── Knowledge Base Articles (6 articles) ───────────────────────────
        article_data = [
            (
                "How to Reset Your Password",
                "account",
                "Step 1: Navigate to https://sso.acme.com/reset. "
                "Step 2: Enter your corporate email address. "
                "Step 3: Follow the link sent to your inbox. "
                "Step 4: Choose a new password meeting complexity requirements (12+ chars, mixed case, number, symbol).",
                ["password", "reset", "account", "login", "sso"],
            ),
            (
                "VPN Setup and Troubleshooting",
                "network",
                "To install the VPN client: download AcmeVPN from https://vpn.acme.com/download. "
                "Run the installer and enter your corporate credentials. "
                "Troubleshooting: 1) Restart the VPN client. 2) Check your internet connection. "
                "3) Ensure your credentials have not expired. 4) Try the EU or US gateway if one is unresponsive.",
                ["vpn", "network", "remote", "connectivity", "gateway"],
            ),
            (
                "Software Installation Requests",
                "software",
                "To request new software: submit a ticket with category 'Software Request'. "
                "Include the software name, version, business justification, and manager approval. "
                "Standard software (listed in the approved catalog) is auto-provisioned within 24 hours. "
                "Non-standard software requires security review (3-5 business days).",
                ["software", "install", "request", "application", "catalog"],
            ),
            (
                "Email Configuration for Mobile Devices",
                "email",
                "For iOS: Settings > Mail > Accounts > Add Account > Microsoft Exchange. "
                "Server: mail.acme.com. Use your corporate email and password. "
                "For Android: Gmail app > Add Account > Exchange. "
                "Server: mail.acme.com. Accept the security policy when prompted.",
                ["email", "mobile", "configuration", "exchange", "phone"],
            ),
            (
                "Printer Setup and Common Issues",
                "hardware",
                "To add a network printer: Settings > Printers > Add Printer. "
                "Enter the printer IP from the label on the device. "
                "Common issues: 1) Paper jam — open front panel and clear obstructions. "
                "2) Offline status — check network cable and restart printer. "
                "3) Driver missing — download from https://printers.acme.com/drivers.",
                ["printer", "hardware", "printing", "driver", "network"],
            ),
            (
                "CRM Access and Permissions",
                "software",
                "To request CRM access: submit a ticket with category 'Access Request'. "
                "Your manager must approve the access level (read-only, standard, admin). "
                "Provisioning takes up to 4 hours after approval. "
                "If locked out, try resetting your CRM password via the CRM login page. "
                "For bulk access requests (new team onboarding), contact IT directly.",
                ["crm", "access", "permissions", "login", "onboarding"],
            ),
        ]
        for i, (title, category, content, tags) in enumerate(article_data, 1):
            aid = generate_id("KB", i)
            self.articles[aid] = KnowledgeBaseArticle(
                article_id=aid, title=title, category=category,
                content=content, tags=tags,
            )

        # ── Pre-existing Tickets (2 tickets) ──────────────────────────────
        tk1 = Ticket(
            ticket_id=generate_id("TK", 1),
            user_id=generate_id("USR", 2),
            subject="Cannot connect to VPN",
            description="I have been unable to connect to the VPN since this morning. The client shows 'Connection timed out' after 30 seconds.",
            status="open",
            priority="high",
            assigned_to="L1 Support",
            created_at="2025-06-01T07:15:00Z",
            updated_at="2025-06-01T07:15:00Z",
            history=[
                {"timestamp": "2025-06-01T07:15:00Z", "action": "created", "note": "Ticket created by user."},
            ],
            related_articles=[generate_id("KB", 2)],
        )
        tk2 = Ticket(
            ticket_id=generate_id("TK", 2),
            user_id=generate_id("USR", 4),
            subject="CRM loading very slowly",
            description="The CRM platform takes over 60 seconds to load any page. This started yesterday afternoon.",
            status="in_progress",
            priority="medium",
            assigned_to="L2 Support",
            created_at="2025-05-31T16:00:00Z",
            updated_at="2025-06-01T09:00:00Z",
            history=[
                {"timestamp": "2025-05-31T16:00:00Z", "action": "created", "note": "Ticket created by user."},
                {"timestamp": "2025-06-01T09:00:00Z", "action": "assigned", "note": "Escalated to L2 Support for investigation."},
            ],
            related_articles=[generate_id("KB", 6)],
        )
        self.tickets[tk1.ticket_id] = tk1
        self.tickets[tk2.ticket_id] = tk2

    # ----- Query methods -----

    def lookup_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def check_system_status(self, system_name: str | None = None) -> list[SystemStatus]:
        if system_name:
            return [
                s for s in self.systems.values()
                if system_name.lower() in s.name.lower()
            ]
        return list(self.systems.values())

    def search_knowledge_base(self, query: str, max_results: int = 5) -> list[KnowledgeBaseArticle]:
        query_lower = query.lower()
        scored: list[tuple[int, KnowledgeBaseArticle]] = []
        for article in self.articles.values():
            score = 0
            if query_lower in article.title.lower():
                score += 3
            if query_lower in article.category.lower():
                score += 2
            for tag in article.tags:
                if query_lower in tag:
                    score += 1
            if query_lower in article.content.lower():
                score += 1
            if score > 0:
                scored.append((score, article))
        scored.sort(key=lambda x: -x[0])
        return [a for _, a in scored[:max_results]]

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        return self.tickets.get(ticket_id)

    # ----- Mutation methods -----

    def create_ticket(
        self,
        user_id: str,
        subject: str,
        description: str,
        priority: str = "medium",
        related_articles: list[str] | None = None,
    ) -> Ticket | None:
        user = self.users.get(user_id)
        if not user:
            return None
        tid = generate_id("TK", self._next_ticket)
        self._next_ticket += 1
        ticket = Ticket(
            ticket_id=tid,
            user_id=user_id,
            subject=subject,
            description=description,
            status="open",
            priority=priority,
            assigned_to="L1 Support",
            created_at="2025-06-01T10:00:00Z",
            updated_at="2025-06-01T10:00:00Z",
            history=[
                {"timestamp": "2025-06-01T10:00:00Z", "action": "created", "note": "Ticket created by user."},
            ],
            related_articles=related_articles or [],
        )
        self.tickets[tid] = ticket
        return ticket

    def update_ticket(
        self,
        ticket_id: str,
        status: str | None = None,
        note: str | None = None,
        priority: str | None = None,
    ) -> Ticket | None:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None
        if status:
            ticket.status = status
        if priority:
            ticket.priority = priority
        ticket.updated_at = "2025-06-01T10:30:00Z"
        ticket.history.append({
            "timestamp": "2025-06-01T10:30:00Z",
            "action": "updated",
            "note": note or f"Status changed to {status or ticket.status}.",
        })
        return ticket

    def escalate_ticket(self, ticket_id: str, reason: str) -> Ticket | None:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            return None
        ticket.status = "escalated"
        ticket.priority = "high"
        ticket.assigned_to = "L2 Support"
        ticket.updated_at = "2025-06-01T11:00:00Z"
        ticket.history.append({
            "timestamp": "2025-06-01T11:00:00Z",
            "action": "escalated",
            "note": f"Escalated to L2 Support. Reason: {reason}",
        })
        return ticket
