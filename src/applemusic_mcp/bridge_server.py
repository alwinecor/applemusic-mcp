"""The original MCP plus tool access to exports for tool-only ChatGPT clients."""

from typing import Literal

from mcp.types import ToolAnnotations

from . import server


def register_exports_tool():
    @server.mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        )
    )
    def exports(action: Literal["list", "read"] = "list", filename: str = "") -> str:
        """Retrieve local Apple Music exports in ChatGPT.

        Use list to find exports, then read with the exact filename. After a tool
        returns an exports:// URI, read its filename here to get the full CSV or
        JSON content. Files live on the MCP host; local paths cannot be downloaded
        by ChatGPT. This exposes the same files as the existing exports resources.
        """
        if action == "list":
            return server.list_exports()
        if not filename:
            return "Error: filename is required for read"
        return server.read_export(filename)


def main():
    register_exports_tool()
    server.main()


if __name__ == "__main__":
    main()
