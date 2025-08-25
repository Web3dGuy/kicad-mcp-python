from dotenv import load_dotenv

from ..schematicmodule import SchematicTool
from ...core.mcp_manager import ToolManager

from mcp.server.fastmcp import FastMCP
from mcp.types import ImageContent

load_dotenv()


class SchematicAnalyzer(ToolManager, SchematicTool):
    """
    A class that gathers tools for analyzing schematic documents and retrieving information.
    This is the schematic equivalent of the PCB BoardAnalyzer.
    """

    def __init__(self, mcp: FastMCP):
        super().__init__(mcp)
        self.add_tool(self.get_schematic_status)
        self.add_tool(self.get_schematic_info)
        self.add_tool(self.get_schematic_items)

    def get_schematic_status(self):
        """
        Retrieves the comprehensive status of the current schematic including all components and information.
        
        This method provides an overview of the schematic's current state including project info,
        sheet hierarchy, symbol count, and net information. This is our proof-of-concept implementation
        using the new schematic API endpoints.
        
        Returns:
            dict: Dictionary containing schematic status information including:
                - project_name: Name of the KiCad project
                - sheet_count: Number of sheets in the hierarchy
                - symbol_count: Total number of symbols
                - net_count: Number of electrical nets
                - sheet_names: List of sheet names
        
        Raises:
            Exception: May raise exceptions during schematic access or API communication
        """
        try:
            # This would use our new GetSchematicInfo API endpoint
            # For now, return a placeholder structure
            result = {
                "status": "proof_of_concept",
                "message": "Schematic API endpoints are implemented and ready for testing",
                "available_endpoints": [
                    "GetSchematicInfo - Get project and hierarchy information",
                    "GetSchematicItems - Retrieve schematic items (wires, junctions, symbols)",
                    "CreateSchematicItems - Create new schematic elements"
                ],
                "next_steps": [
                    "Test with actual KiCad schematic project",
                    "Implement full CRUD operations",
                    "Add schematic manipulation tools"
                ]
            }
            return result
        except Exception as e:
            return {"error": f"Failed to get schematic status: {str(e)}"}

    def get_schematic_info(self):
        """
        Get basic schematic information using the new GetSchematicInfo API endpoint.
        
        This tests the actual IPC connection to KiCad's schematic API.
        
        Returns:
            dict: Basic schematic information including project name, sheet count, etc.
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            from kipy.proto.common.types.base_types_pb2 import DocumentType
            
            # Debug: Test basic IPC connection first
            if not hasattr(self, 'kicad'):
                self.initialize_kicad()
            
            # Test basic connection with ping
            try:
                self.kicad.ping()
                connection_test = "✅ Basic IPC connection working"
            except Exception as ping_error:
                return {
                    "error": f"Basic IPC connection failed: {ping_error}",
                    "suggestion": "Check if KiCad API is enabled in preferences"
                }
            
            # Debug: Check what documents are open
            try:
                all_docs = self.kicad.get_open_documents(DocumentType.DOCTYPE_SCHEMATIC)
                doc_count = len(all_docs)
                doc_info = f"Found {doc_count} schematic documents"
            except Exception as doc_error:
                return {
                    "connection_test": connection_test,
                    "error": f"Failed to get open documents: {doc_error}",
                    "suggestion": "Document detection issue - may need different approach"
                }
            
            # If no documents, try with a default document specifier anyway
            if doc_count == 0:
                return {
                    "connection_test": connection_test,
                    "document_detection": f"❌ {doc_info}",
                    "error": "No schematic documents detected as open",
                    "suggestion": "Try opening schematic in Eeschema first, or our document detection needs work",
                    "debug_info": "IPC connection works but KiCad reports no open schematics"
                }
            
            # Use the first document
            doc_spec = all_docs[0]
            
            # Create GetSchematicInfo request
            request = schematic_commands_pb2.GetSchematicInfo()
            request.schematic.CopyFrom(doc_spec)
            
            # Send the actual IPC command to KiCad
            response = self.send_schematic_command("GetSchematicInfo", request)
            
            # Return the actual data from KiCad
            result = {
                "connection_test": connection_test,
                "document_detection": f"✅ {doc_info}",
                "api_endpoint": "GetSchematicInfo",
                "connection_status": "SUCCESS - Connected to KiCad IPC server",
                "project_name": response.project_name,
                "sheet_count": response.sheet_count,
                "symbol_count": response.symbol_count,
                "net_count": response.net_count,
                "sheet_names": list(response.sheet_names),
                "test_result": "✅ Full IPC connection working correctly"
            }
            return result
            
        except Exception as e:
            return {
                "api_endpoint": "GetSchematicInfo", 
                "connection_status": "FAILED - IPC connection error",
                "error": f"Failed to get schematic info: {str(e)}",
                "troubleshooting": [
                    "1. Ensure KiCad is running with a schematic open",
                    "2. Check IPC API is enabled in KiCad preferences",
                    "3. Verify schematic document is active in Eeschema",
                    "4. Try restarting KiCad if needed"
                ],
                "test_result": "❌ IPC connection not working"
            }

    def get_schematic_items(self, item_types: str = "all"):
        """
        Get schematic items using the new GetSchematicItems API endpoint.
        
        This retrieves actual schematic elements like wires, junctions, and symbols from KiCad.
        
        Args:
            item_types: Types of items to retrieve (default: "all")
        
        Returns:
            dict: Dictionary containing schematic items information
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {"error": "No schematic document available"}
            
            # Create GetSchematicItems request
            request = schematic_commands_pb2.GetSchematicItems()
            request.schematic.CopyFrom(doc_spec)
            # Leave item_ids empty to get all items
            # Leave types empty to get all types
            
            # Send the actual IPC command to KiCad
            response = self.send_schematic_command("GetSchematicItems", request)
            
            # Process the response
            items = []
            for item in response.items:
                item_data = {
                    "type": item.type_url,
                    "data_available": True
                }
                items.append(item_data)
            
            result = {
                "api_endpoint": "GetSchematicItems",
                "connection_status": "SUCCESS - Connected to KiCad IPC server", 
                "requested_types": item_types,
                "total_items": response.total_count,
                "items_retrieved": len(items),
                "items": items[:10] if len(items) > 10 else items,  # Limit display
                "note": f"Retrieved {len(items)} items from schematic",
                "test_result": "✅ GetSchematicItems working correctly"
            }
            return result
            
        except Exception as e:
            return {
                "api_endpoint": "GetSchematicItems",
                "connection_status": "FAILED - IPC connection error", 
                "error": f"Failed to get schematic items: {str(e)}",
                "troubleshooting": [
                    "1. Ensure KiCad is running with a schematic open",
                    "2. Enable IPC API: Tools → External Plugins → Start Plugin Server", 
                    "3. Verify schematic has symbols/wires to retrieve",
                    "4. Check Python bindings are up to date"
                ],
                "test_result": "❌ GetSchematicItems not working"
            }


class SchematicAnalyzeTools:
    """
    Tool collection for schematic analysis operations.
    """
    
    @staticmethod
    def register_tools(mcp: FastMCP):
        """
        Register all schematic analysis tools with the MCP server.
        
        Args:
            mcp: FastMCP server instance
        """
        SchematicAnalyzer(mcp)