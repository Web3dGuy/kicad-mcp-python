from dotenv import load_dotenv

from ..schematicmodule import SchematicTool
from ...core.mcp_manager import ToolManager

from mcp.server.fastmcp import FastMCP

load_dotenv()


class SchematicLibraryManager(ToolManager, SchematicTool):
    """
    A class that provides tools for managing symbol libraries.
    Unified library management that matches KiCad UI behavior exactly.
    """

    def __init__(self, mcp: FastMCP):
        super().__init__(mcp)

        # Unified library management tool
        self.add_tool(self.manage_symbol_libraries)


class SchematicLibraryTools:
    """Factory class for registering library management tools with MCP."""

    @staticmethod
    def register_tools(mcp: FastMCP):
        """Register all library management tools with the MCP server."""
        SchematicLibraryManager(mcp)