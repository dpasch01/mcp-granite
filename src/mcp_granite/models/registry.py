"""Model registry mapping friendly names to ADK-compatible model objects."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from google.adk.models.lite_llm import LiteLlm

logger = logging.getLogger(__name__)


@dataclass
class ModelSpec:
    """Specification for a model in the benchmark."""

    litellm_id: str | None = None
    google_model: str | None = None
    size_class: str = "unknown"  # tiny, small, medium, large, xl, frontier
    parameter_count: str | None = None  # e.g., "7B", "70B"
    local: bool = False

    @property
    def display_name(self) -> str:
        if self.google_model:
            return self.google_model
        return self.litellm_id or "unknown"


# ── Registry ─────────────────────────────────────────────────────────────────

MODELS: dict[str, ModelSpec] = {
    # --- Frontier APIs ---
    "gpt-4o": ModelSpec(
        litellm_id="openai/gpt-4o", size_class="frontier",
    ),
    "gpt-4o-mini": ModelSpec(
        litellm_id="openai/gpt-4o-mini", size_class="frontier",
    ),
    "claude-sonnet": ModelSpec(
        litellm_id="anthropic/claude-sonnet-4-20250514", size_class="frontier",
    ),
    "claude-haiku": ModelSpec(
        litellm_id="anthropic/claude-haiku-4-5-20251001", size_class="frontier",
    ),
    "gemini-2.0-flash": ModelSpec(
        google_model="gemini-2.0-flash", size_class="frontier",
    ),
    "gemini-2.5-flash": ModelSpec(
        google_model="gemini-2.5-flash-preview-05-20", size_class="frontier",
    ),
    # --- Local via Ollama (XL) ---
    "llama3.3-70b": ModelSpec(
        litellm_id="ollama_chat/llama3.3:70b", size_class="xl",
        parameter_count="70B", local=True,
    ),
    "qwen2.5-72b": ModelSpec(
        litellm_id="ollama_chat/qwen2.5:72b", size_class="xl",
        parameter_count="72B", local=True,
    ),
    # --- Local via Ollama (Large) ---
    "qwen2.5-32b": ModelSpec(
        litellm_id="ollama_chat/qwen2.5:32b", size_class="large",
        parameter_count="32B", local=True,
    ),
    # --- Local via Ollama (Medium) ---
    "llama3.1-8b": ModelSpec(
        litellm_id="ollama_chat/llama3.1:8b", size_class="medium",
        parameter_count="8B", local=True,
    ),
    "qwen2.5-7b": ModelSpec(
        litellm_id="ollama_chat/qwen2.5:7b", size_class="medium",
        parameter_count="7B", local=True,
    ),
    # --- Local via Ollama (Small) ---
    "llama3.2-3b": ModelSpec(
        litellm_id="ollama_chat/llama3.2:3b", size_class="small",
        parameter_count="3B", local=True,
    ),
    "phi3.5-mini": ModelSpec(
        litellm_id="ollama_chat/phi3.5:3.8b", size_class="small",
        parameter_count="3.8B", local=True,
    ),
    # --- Local via Ollama (Tiny) ---
    "qwen2.5-1.5b": ModelSpec(
        litellm_id="ollama_chat/qwen2.5:1.5b", size_class="tiny",
        parameter_count="1.5B", local=True,
    ),
    "gemma2-2b": ModelSpec(
        litellm_id="ollama_chat/gemma2:2b", size_class="tiny",
        parameter_count="2B", local=True,
    ),
}


def _resolve_adhoc_spec(model_name: str) -> ModelSpec | None:
    """Try to build a ModelSpec for a model name not in the registry.

    Supports:
      - Ollama tags like "llama3.2:latest", "qwen2.5:3b-instruct"
        → routed as "ollama_chat/<model_name>"
      - LiteLLM-style IDs like "openai/gpt-4o", "anthropic/claude-..."
        → passed through directly
    """
    if ":" in model_name:
        # Ollama tag — may include slashes for namespaced models
        # e.g. "llama3.2:latest", "hf.co/Salesforce/xLAM:Q8_0",
        #      "robbiemu/Salesforce_Llama-xLAM-2:8b-fc-r-q3_K_M"
        return ModelSpec(
            litellm_id=f"ollama_chat/{model_name}",
            size_class="unknown",
            local=True,
        )
    if "/" in model_name:
        # Looks like a LiteLLM provider/model ID  (e.g. "openai/gpt-4o")
        return ModelSpec(litellm_id=model_name, size_class="unknown")
    return None


def get_adk_model(model_name: str) -> Any:
    """Return an ADK-compatible model object for the given model name.

    For Google models, returns a string (ADK handles Gemini natively).
    For all others, returns a LiteLlm wrapper.

    Models not in the registry are resolved as ad-hoc Ollama tags
    (if they contain ':') or raw LiteLLM IDs (if they contain '/').
    """
    spec = MODELS.get(model_name) or _resolve_adhoc_spec(model_name)
    if spec is None:
        raise ValueError(
            f"Unknown model '{model_name}'. "
            f"Registered: {list(MODELS.keys())}. "
            f"You can also pass Ollama tags (e.g. 'llama3.2:latest') or "
            f"LiteLLM IDs (e.g. 'openai/gpt-4o') directly."
        )
    if spec.google_model:
        return spec.google_model
    if spec.litellm_id:
        kwargs = {}
        if spec.local:
            num_ctx = int(os.environ.get("OLLAMA_CONTEXT_SIZE", "8192"))
            kwargs["num_ctx"] = num_ctx
        return LiteLlm(model=spec.litellm_id, **kwargs)
    raise ValueError(f"Model '{model_name}' has no litellm_id or google_model configured.")


def get_model_spec(model_name: str) -> ModelSpec:
    """Return the ModelSpec for a given model name (or build one ad-hoc)."""
    spec = MODELS.get(model_name) or _resolve_adhoc_spec(model_name)
    if spec is None:
        raise ValueError(
            f"Unknown model '{model_name}'. "
            f"Registered: {list(MODELS.keys())}. "
            f"You can also pass Ollama tags (e.g. 'llama3.2:latest') or "
            f"LiteLLM IDs (e.g. 'openai/gpt-4o') directly."
        )
    return spec


def list_models() -> list[str]:
    """Return all registered model names."""
    return list(MODELS.keys())


def _get_ollama_tag(spec: ModelSpec) -> str | None:
    """Extract the Ollama model tag from a ModelSpec, if it's an Ollama model."""
    if spec.litellm_id and spec.litellm_id.startswith("ollama_chat/"):
        return spec.litellm_id.removeprefix("ollama_chat/")
    return None


def _fetch_ollama_models(base_url: str = "http://localhost:11434") -> set[str]:
    """Query the Ollama API for locally available model tags."""
    req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
    return {m["name"] for m in data.get("models", [])}


def _normalize_ollama_tag(tag: str) -> str:
    """Normalize an Ollama tag for comparison (append :latest if no tag)."""
    return tag if ":" in tag else f"{tag}:latest"


def preflight_check_models(model_names: list[str]) -> None:
    """Verify that all requested Ollama models are locally available.

    Raises click.ClickException with an actionable message listing
    missing models and the exact pull commands to fix the issue.
    """
    import click

    # Collect Ollama tags we need to verify
    needed: dict[str, str] = {}  # ollama_tag -> friendly_name
    for name in model_names:
        spec = MODELS.get(name) or _resolve_adhoc_spec(name)
        if spec is None:
            continue
        tag = _get_ollama_tag(spec)
        if tag is not None:
            needed[tag] = name

    if not needed:
        return

    # Query Ollama
    try:
        available_raw = _fetch_ollama_models()
    except urllib.error.URLError:
        raise click.ClickException(
            "Cannot connect to Ollama at http://localhost:11434.\n"
            "Is Ollama running?  Start it with:  ollama serve"
        )
    except Exception as exc:
        logger.warning("Could not query Ollama for preflight check: %s", exc)
        return

    available = {_normalize_ollama_tag(t) for t in available_raw}

    missing: list[tuple[str, str]] = []
    for tag, friendly in needed.items():
        if _normalize_ollama_tag(tag) not in available:
            missing.append((friendly, tag))

    if missing:
        lines = [
            f"The following Ollama model(s) are not available locally:\n",
        ]
        for friendly, tag in missing:
            lines.append(f"  - {friendly}  (ollama tag: {tag})")
        lines.append("\nPull them first:")
        for _, tag in missing:
            lines.append(f"  ollama pull {tag}")
        raise click.ClickException("\n".join(lines))


def _fetch_ollama_model_details(
    base_url: str = "http://localhost:11434",
) -> dict[str, str]:
    """Query Ollama /api/tags and return {name: parameter_size} mapping.

    Returns an empty dict if Ollama is unreachable.
    """
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
    except Exception:
        return {}

    details: dict[str, str] = {}
    for m in data.get("models", []):
        name = m.get("name", "")
        # parameter_size lives in m["details"]["parameter_size"] (e.g. "3.2B")
        param_size = (m.get("details") or {}).get("parameter_size", "")
        if name and param_size:
            details[name] = param_size
    return details


def _parse_param_size_from_tag(model_name: str) -> str | None:
    """Try to extract a parameter size from the Ollama tag itself.

    Examples:
        "hermes3:8b"       → "8B"
        "qwen2.5:1.5b"     → "1.5B"
        "llama3.2:latest"  → None  (no size in tag)
    """
    import re

    # Look for a numeric size suffix like :8b, :1.5b, :70b-instruct, etc.
    match = re.search(r":(\d+(?:\.\d+)?)[bB]", model_name)
    if match:
        return f"{match.group(1)}B"
    return None


def resolve_parameter_count(
    model_name: str,
    ollama_details: dict[str, str] | None = None,
) -> str:
    """Resolve parameter count for a model using multi-tier lookup.

    Order: (1) MODELS registry, (2) Ollama API details, (3) tag parsing, (4) "?".
    """
    # 1. Registry lookup
    spec = MODELS.get(model_name)
    if spec and spec.parameter_count:
        return spec.parameter_count

    # 2. Ollama API details
    if ollama_details:
        # Try exact match first, then normalized
        if model_name in ollama_details:
            return ollama_details[model_name]
        normalized = _normalize_ollama_tag(model_name)
        if normalized in ollama_details:
            return ollama_details[normalized]

    # 3. Tag parsing
    parsed = _parse_param_size_from_tag(model_name)
    if parsed:
        return parsed

    return "?"
