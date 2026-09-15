"""Factory for creating ADK agents wired to MCP servers."""

from __future__ import annotations

import importlib
import os
import sys

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

from edgetoolbench.mcp_servers._base import FaultConfig
from edgetoolbench.models.registry import get_adk_model

# Base system instruction for all benchmark agents
BASE_INSTRUCTION = """\
You are a helpful assistant that uses the available tools to complete the user's request.
Always use tools when they are relevant. Do not make up information — rely on tool results.
When a tool call fails, you may retry or try an alternative approach.
After completing the task, provide a clear summary of what was done.
"""


def _resolve_server_module(domain: str, granularity: str) -> str:
    """Resolve the Python module path for a domain + granularity server.

    Convention: edgetoolbench.mcp_servers.{domain}.{granularity}_server
    """
    module_path = f"edgetoolbench.mcp_servers.{domain}.{granularity}_server"
    try:
        importlib.import_module(module_path)
    except ModuleNotFoundError:
        raise ValueError(
            f"No server module for domain='{domain}', granularity='{granularity}'. "
            f"Expected module: {module_path}"
        )
    return module_path


def _build_connection_params(
    domain: str,
    granularity: str,
    fault_config: FaultConfig,
) -> StdioConnectionParams:
    """Build MCP stdio connection parameters for a given server."""
    module_path = _resolve_server_module(domain, granularity)

    env = {**os.environ, "FAULT_CONFIG": fault_config.to_json()}

    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", module_path],
            env=env,
        ),
        timeout=10.0,
    )


def create_agent_and_toolset(
    model_name: str,
    domain: str,
    granularity: str,
    fault_config: FaultConfig,
    instruction: str | None = None,
) -> tuple[LlmAgent, McpToolset]:
    """Create an ADK agent connected to the appropriate MCP server.

    Returns (agent, toolset). Caller must `await toolset.close()` after use.
    """
    model = get_adk_model(model_name)
    conn_params = _build_connection_params(domain, granularity, fault_config)
    toolset = McpToolset(connection_params=conn_params)

    agent = LlmAgent(
        model=model,
        name="benchmark_agent",
        instruction=instruction or BASE_INSTRUCTION,
        tools=[toolset],
    )

    return agent, toolset
