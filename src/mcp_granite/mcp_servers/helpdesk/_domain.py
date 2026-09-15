"""Domain models for the IT Helpdesk mock."""

from __future__ import annotations

from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    name: str
    email: str
    department: str
    role: str


class SystemStatus(BaseModel):
    system_id: str
    name: str
    status: str  # "operational", "degraded", "down"
    last_checked: str
    message: str


class KnowledgeBaseArticle(BaseModel):
    article_id: str
    title: str
    category: str
    content: str
    tags: list[str]


class Ticket(BaseModel):
    ticket_id: str
    user_id: str
    subject: str
    description: str
    status: str  # "open", "in_progress", "escalated", "resolved", "closed"
    priority: str  # "low", "medium", "high", "critical"
    assigned_to: str
    created_at: str
    updated_at: str
    history: list[dict]
    related_articles: list[str]
