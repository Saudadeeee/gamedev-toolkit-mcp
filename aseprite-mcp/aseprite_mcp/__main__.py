import anyio

from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from . import mcp
from .tools import *  # noqa: F401,F403


async def run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await mcp._mcp_server.run(  # type: ignore[attr-defined]
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=mcp.name,
                server_version="0.1.0",
                capabilities=mcp._mcp_server.get_capabilities(  # type: ignore[attr-defined]
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                instructions=None,
            ),
        )


if __name__ == "__main__":
    anyio.run(run_stdio)
