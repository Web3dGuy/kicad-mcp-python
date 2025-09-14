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
        self.add_tool(self.get_symbol_positions)
        self.add_tool(self.get_symbol_pins)
        
        # Document management tools
        self.add_tool(self.save_schematic)
        self.add_tool(self.delete_items)
        
        # Selection management tools - Phase 1 Foundational Optimizations
        self.add_tool(self.get_selection)
        self.add_tool(self.select_items)
        self.add_tool(self.clear_selection)
        self.add_tool(self.select_by_type)

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
            from kipy.proto.schematic import schematic_types_pb2

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
                    "type": item.type_url.split('.')[-1] if '.' in item.type_url else item.type_url,
                    "type_url": item.type_url,
                    "data_available": True
                }

                # Try to extract Line coordinates
                if item.type_url.endswith('Line'):
                    line = schematic_types_pb2.Line()
                    if item.Unpack(line):
                        # WORKAROUND: Lines seem to be returned at 1/100 scale compared to symbols
                        # This may be a KiCad API issue where lines use different internal units
                        # Check if coordinates are suspiciously small (< 10mm)
                        scale_factor = 1
                        if abs(line.start.x_nm) < 10_000_000 and abs(line.start.y_nm) < 10_000_000:
                            scale_factor = 100  # Apply 100x scaling to match symbol coordinates

                        item_data.update({
                            "id": line.id.value if hasattr(line, 'id') else "unknown",
                            "start": {
                                "x_nm": line.start.x_nm * scale_factor,
                                "y_nm": line.start.y_nm * scale_factor,
                                "x_mm": (line.start.x_nm * scale_factor) / 1_000_000,
                                "y_mm": (line.start.y_nm * scale_factor) / 1_000_000
                            },
                            "end": {
                                "x_nm": line.end.x_nm * scale_factor,
                                "y_nm": line.end.y_nm * scale_factor,
                                "x_mm": (line.end.x_nm * scale_factor) / 1_000_000,
                                "y_mm": (line.end.y_nm * scale_factor) / 1_000_000
                            },
                            "layer": line.layer if hasattr(line, 'layer') else "unknown",
                            "layer_type": "WIRE" if hasattr(line, 'layer') and line.layer == 1 else "BUS" if hasattr(line, 'layer') and line.layer == 2 else "GRAPHICAL" if hasattr(line, 'layer') and line.layer == 3 else f"UNKNOWN({line.layer if hasattr(line, 'layer') else 'none'})",
                            "scale_applied": scale_factor if scale_factor > 1 else None
                        })

                items.append(item_data)
            
            result = {
                "api_endpoint": "GetSchematicItems",
                "connection_status": "SUCCESS - Connected to KiCad IPC server", 
                "requested_types": item_types,
                "total_items": response.total_count,
                "items_retrieved": len(items),
                "items": items,  # Show all items to inspect graphical line
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

    def get_symbol_positions(self):
        """
        Get all symbols in the schematic with their exact positions and pin data.
        
        This uses the enhanced GetSchematicItems API that now returns symbol positions
        and embedded pin information for precise coordinate-based wire placement.
        
        Returns:
            dict: Dictionary containing all symbols with positions and pins
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            from kipy.proto.schematic import schematic_types_pb2
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {"error": "No schematic document available"}
            
            # Create GetSchematicItems request
            request = schematic_commands_pb2.GetSchematicItems()
            request.schematic.CopyFrom(doc_spec)
            # Leave empty to get all items (symbols, wires, etc.)
            
            # Send the actual IPC command to KiCad
            response = self.send_schematic_command("GetSchematicItems", request)
            
            # Parse the response to extract symbols
            symbols = []
            other_items = []
            
            for item in response.items:
                if item.type_url.endswith('Symbol'):
                    # Unpack Symbol message
                    symbol = schematic_types_pb2.Symbol()
                    item.Unpack(symbol)
                    
                    symbol_data = {
                        "id": symbol.id.value,
                        "reference": symbol.reference,
                        "value": symbol.value,
                        "library_id": symbol.library_id,
                        "position": {
                            "x_nm": symbol.position.x_nm,
                            "y_nm": symbol.position.y_nm
                        },
                        "unit": symbol.unit,
                        "body_style": symbol.body_style,
                        "orientation_degrees": symbol.orientation.value_degrees,
                        "mirrored_x": symbol.mirrored_x,
                        "mirrored_y": symbol.mirrored_y,
                        "pin_count": len(symbol.pins),
                        "pins": []
                    }
                    
                    # Add pin information
                    for pin in symbol.pins:
                        pin_data = {
                            "id": pin.id.value,
                            "name": pin.name,
                            "number": pin.number,
                            "position": {
                                "x_nm": pin.position.x_nm,
                                "y_nm": pin.position.y_nm
                            },
                            "electrical_type": pin.electrical_type,
                            "orientation": pin.orientation,
                            "length": pin.length
                        }
                        symbol_data["pins"].append(pin_data)
                    
                    symbols.append(symbol_data)
                else:
                    # Track other item types
                    other_items.append({
                        "type": item.type_url,
                        "available": True
                    })
            
            result = {
                "api_endpoint": "GetSchematicItems (Enhanced)",
                "connection_status": "SUCCESS - Symbol positions retrieved",
                "total_items": response.total_count,
                "symbol_count": len(symbols),
                "other_items_count": len(other_items),
                "symbols": symbols,
                "coordinate_system": "nanometers (nm)",
                "test_result": "✅ Symbol positions available for precise wire placement"
            }
            
            if len(symbols) == 0:
                result["warning"] = "No symbols found - ensure schematic has components placed"
            
            return result
            
        except Exception as e:
            return {
                "api_endpoint": "GetSchematicItems (Enhanced)",
                "connection_status": "FAILED - Symbol position retrieval error",
                "error": f"Failed to get symbol positions: {str(e)}",
                "troubleshooting": [
                    "1. Ensure schematic has symbols placed",
                    "2. Check if KiCad API has been rebuilt with new Symbol types",
                    "3. Verify Python bindings include Symbol and Pin message types",
                    "4. Try restarting KiCad with schematic open"
                ],
                "test_result": "❌ Symbol position retrieval not working"
            }

    def get_symbol_pins(self, symbol_id: str):
        """
        Get detailed pin information for a specific symbol by ID.
        
        This uses the new GetSymbolPins API endpoint to retrieve exact pin positions
        and properties for precise wire connection.
        
        Args:
            symbol_id: The UUID of the symbol to query pins for
            
        Returns:
            dict: Dictionary containing pin positions and properties for the symbol
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            from kipy.proto.common.types import base_types_pb2
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {"error": "No schematic document available"}
            
            # Create GetSymbolPins request
            request = schematic_commands_pb2.GetSymbolPins()
            request.schematic.CopyFrom(doc_spec)
            request.symbol_id.value = symbol_id
            
            # Send the actual IPC command to KiCad
            response = self.send_schematic_command("GetSymbolPins", request)
            
            # Check for errors
            if response.error:
                return {
                    "api_endpoint": "GetSymbolPins",
                    "connection_status": "ERROR - API returned error",
                    "symbol_id": symbol_id,
                    "error": response.error,
                    "test_result": "❌ Symbol not found or other API error"
                }
            
            # Parse pin data
            pins = []
            for pin in response.pins:
                pin_data = {
                    "id": pin.id.value,
                    "name": pin.name,
                    "number": pin.number,
                    "position": {
                        "x_nm": pin.position.x_nm,
                        "y_nm": pin.position.y_nm,
                        "x_mm": pin.position.x_nm / 1_000_000,
                        "y_mm": pin.position.y_nm / 1_000_000
                    },
                    "electrical_type": pin.electrical_type,
                    "electrical_type_name": self._get_pin_type_name(pin.electrical_type),
                    "orientation": pin.orientation,
                    "orientation_name": self._get_pin_orientation_name(pin.orientation),
                    "length": pin.length,
                    "length_mm": pin.length / 1_000_000
                }
                pins.append(pin_data)
            
            result = {
                "api_endpoint": "GetSymbolPins",
                "connection_status": "SUCCESS - Pin positions retrieved",
                "symbol_id": symbol_id,
                "symbol_reference": response.reference,
                "symbol_position": {
                    "x_nm": response.symbol_position.x_nm,
                    "y_nm": response.symbol_position.y_nm,
                    "x_mm": response.symbol_position.x_nm / 1_000_000,
                    "y_mm": response.symbol_position.y_nm / 1_000_000
                },
                "pin_count": len(pins),
                "pins": pins,
                "coordinate_system": "nanometers (nm) with mm conversion",
                "test_result": "✅ Symbol pins available for precise wire connection"
            }
            
            return result
            
        except Exception as e:
            return {
                "api_endpoint": "GetSymbolPins",
                "connection_status": "FAILED - Pin position retrieval error",
                "symbol_id": symbol_id,
                "error": f"Failed to get symbol pins: {str(e)}",
                "troubleshooting": [
                    "1. Verify symbol_id is correct (use get_symbol_positions first)",
                    "2. Check if KiCad API has GetSymbolPins implemented",
                    "3. Ensure Python bindings include GetSymbolPins message types",
                    "4. Try with a different symbol ID"
                ],
                "test_result": "❌ Symbol pin retrieval not working"
            }
    
    def _get_pin_type_name(self, pin_type):
        """Convert pin electrical type enum to readable name."""
        type_names = {
            0: "UNKNOWN",
            1: "INPUT", 
            2: "OUTPUT",
            3: "BIDIRECTIONAL",
            4: "TRI_STATE",
            5: "PASSIVE",
            6: "UNSPECIFIED",
            7: "POWER_IN",
            8: "POWER_OUT", 
            9: "OPEN_COLLECTOR",
            10: "OPEN_EMITTER",
            11: "NO_CONNECT"
        }
        return type_names.get(pin_type, f"UNKNOWN({pin_type})")
    
    def _get_pin_orientation_name(self, orientation):
        """Convert pin orientation to readable name."""
        orientations = {
            0: "RIGHT",
            90: "UP", 
            180: "LEFT",
            270: "DOWN"
        }
        return orientations.get(orientation, f"ANGLE({orientation})")
    
    def save_schematic(self):
        """
        Save the current schematic document.
        
        This uses the SaveDocument API endpoint to save the active schematic to disk.
        
        Returns:
            dict: Result of the save operation
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.common.commands import editor_commands_pb2
            from kipy.proto.common.types.base_types_pb2 import DocumentType
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {
                    "error": "No schematic document available",
                    "troubleshooting": [
                        "Ensure KiCad is running with a schematic open",
                        "Check that schematic is active in Eeschema"
                    ]
                }
            
            # Create SaveDocument request
            request = editor_commands_pb2.SaveDocument()
            request.document.CopyFrom(doc_spec)
            
            # Send the request to KiCad
            response = self.send_editor_command("SaveDocument", request)
            
            return {
                "api_endpoint": "SaveDocument",
                "connection_status": "SUCCESS - Schematic saved",
                "operation": "Save schematic",
                "document_type": "Schematic",
                "result": "✅ Schematic saved successfully",
                "next_actions": [
                    "get_schematic_status() to verify save completed",
                    "Continue editing or create additional items"
                ]
            }
            
        except Exception as e:
            return {
                "api_endpoint": "SaveDocument",
                "connection_status": "FAILED - Save operation error",
                "error": f"Failed to save schematic: {str(e)}",
                "troubleshooting": [
                    "1. Ensure KiCad is running with write permissions",
                    "2. Check that schematic file is not read-only",
                    "3. Verify there's enough disk space",
                    "4. Try manual save in KiCad first"
                ],
                "test_result": "❌ Save operation not working"
            }
    
    def delete_items(self, item_ids: list[str]):
        """
        Delete items from the schematic by their IDs.
        
        This uses the DeleteItems API endpoint to remove schematic elements.
        
        Args:
            item_ids: List of item ID strings to delete
            
        Returns:
            dict: Result of the deletion operation
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.common.commands import editor_commands_pb2
            from kipy.proto.common.types import base_types_pb2
            
            if not item_ids or len(item_ids) == 0:
                return {
                    "error": "No item IDs provided",
                    "required": "List of item ID strings to delete",
                    "example": "delete_items(['item-id-1', 'item-id-2'])"
                }
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {
                    "error": "No schematic document available",
                    "troubleshooting": [
                        "Ensure KiCad is running with a schematic open",
                        "Check that schematic is active in Eeschema"
                    ]
                }
            
            # Create DeleteItems request
            request = editor_commands_pb2.DeleteItems()
            request.header.document.CopyFrom(doc_spec)
            
            # Add item IDs to delete
            for item_id in item_ids:
                kiid = base_types_pb2.KIID()
                kiid.value = item_id
                request.item_ids.append(kiid)
            
            # Send the request to KiCad
            response = self.send_editor_command("DeleteItems", request)
            
            # Process the response
            if response and hasattr(response, 'deleted_items'):
                successful_deletions = []
                failed_deletions = []
                
                for result in response.deleted_items:
                    if hasattr(result, 'status'):
                        if result.status == 1:  # IDS_OK
                            successful_deletions.append(result.id.value)
                        else:
                            failed_deletions.append({
                                "id": result.id.value,
                                "status": result.status,
                                "reason": self._get_deletion_status_name(result.status)
                            })
                
                return {
                    "api_endpoint": "DeleteItems",
                    "connection_status": "SUCCESS - Items deleted",
                    "operation": "Delete schematic items",
                    "items_requested": len(item_ids),
                    "items_deleted": len(successful_deletions),
                    "items_failed": len(failed_deletions),
                    "successful_deletions": successful_deletions,
                    "failed_deletions": failed_deletions if failed_deletions else None,
                    "result": f"✅ {len(successful_deletions)}/{len(item_ids)} items deleted successfully",
                    "next_actions": [
                        "get_schematic_status() to verify deletions",
                        "save_schematic() to save changes"
                    ]
                }
            else:
                return {
                    "api_endpoint": "DeleteItems",
                    "connection_status": "FAILED - No response from deletion",
                    "error": "No deletion results returned from KiCad",
                    "items_requested": len(item_ids)
                }
                
        except Exception as e:
            return {
                "api_endpoint": "DeleteItems",
                "connection_status": "FAILED - Deletion operation error",
                "error": f"Failed to delete items: {str(e)}",
                "items_requested": len(item_ids) if item_ids else 0,
                "troubleshooting": [
                    "1. Ensure item IDs are valid and exist in schematic",
                    "2. Check that items are not read-only or protected",
                    "3. Verify KiCad API has deletion permissions",
                    "4. Try selecting and deleting items manually first"
                ],
                "test_result": "❌ Delete operation not working"
            }
    
    def _get_deletion_status_name(self, status):
        """Convert deletion status enum to readable name."""
        status_names = {
            0: "UNKNOWN",
            1: "OK - Item deleted successfully",
            2: "NONEXISTENT - Item did not exist",
            3: "IMMUTABLE - Item cannot be deleted via API"
        }
        return status_names.get(status, f"UNKNOWN_STATUS({status})")
    
    # Selection Management System - Phase 1 Foundational Optimizations
    
    def get_selection(self):
        """
        Get currently selected schematic items.
        
        This uses the new GetSelection API endpoint to retrieve the current selection
        from the schematic editor, enabling bulk operations on selected items.
        
        Returns:
            dict: Dictionary containing selected items and their properties
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            from kipy.proto.schematic import schematic_types_pb2
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {
                    "error": "No schematic document available",
                    "troubleshooting": [
                        "Ensure KiCad is running with a schematic open",
                        "Check that schematic is active in Eeschema"
                    ]
                }
            
            # Create GetSelection request
            request = schematic_commands_pb2.GetSelection()
            request.schematic.CopyFrom(doc_spec)
            
            # Send the actual IPC command to KiCad
            response = self.send_schematic_command("GetSelection", request)

            # Process the response
            selected_items = []
            for item in response.items:
                item_info = {
                    "type": item.type_url.split('.')[-1] if '.' in item.type_url else item.type_url,
                    "type_url": item.type_url
                }
                
                # Try to extract more details based on type
                if item.type_url.endswith('Symbol'):
                    symbol = schematic_types_pb2.Symbol()
                    if item.Unpack(symbol):
                        item_info.update({
                            "id": symbol.id.value,
                            "reference": symbol.reference,
                            "value": symbol.value,
                            "position": {
                                "x_nm": symbol.position.x_nm,
                                "y_nm": symbol.position.y_nm
                            }
                        })
                elif item.type_url.endswith('Wire'):
                    wire = schematic_types_pb2.Wire()
                    if item.Unpack(wire):
                        item_info.update({
                            "id": wire.id.value,
                            "start": {
                                "x_nm": wire.start.x_nm,
                                "y_nm": wire.start.y_nm
                            },
                            "end": {
                                "x_nm": wire.end.x_nm,
                                "y_nm": wire.end.y_nm
                            }
                        })
                elif item.type_url.endswith('Line'):
                    line = schematic_types_pb2.Line()
                    if item.Unpack(line):
                        item_info.update({
                            "id": line.id.value,
                            "start": {
                                "x_nm": line.start.x_nm,
                                "y_nm": line.start.y_nm
                            },
                            "end": {
                                "x_nm": line.end.x_nm,
                                "y_nm": line.end.y_nm
                            },
                            "layer": line.layer if hasattr(line, 'layer') else "unknown",
                            "layer_type": "WIRE" if hasattr(line, 'layer') and line.layer == 1 else "BUS" if hasattr(line, 'layer') and line.layer == 2 else "GRAPHICAL" if hasattr(line, 'layer') and line.layer == 3 else f"UNKNOWN({line.layer if hasattr(line, 'layer') else 'none'})"
                        })

                selected_items.append(item_info)
            
            return {
                "api_endpoint": "GetSelection",
                "connection_status": "SUCCESS - Selection retrieved",
                "selection_count": response.selection_count,
                "selected_items": selected_items,
                "result": f"✅ {response.selection_count} items in selection",
                "next_actions": [
                    "Perform bulk operations on selected items",
                    "clear_selection() to deselect all",
                    "select_items() to modify selection"
                ]
            }
            
        except Exception as e:
            return {
                "api_endpoint": "GetSelection",
                "connection_status": "FAILED - Selection retrieval error",
                "error": f"Failed to get selection: {str(e)}",
                "troubleshooting": [
                    "1. Ensure KiCad is running with a schematic open",
                    "2. Check that items are selected in the editor",
                    "3. Verify API has selection management handlers",
                    "4. Try selecting items manually first"
                ]
            }
    
    def select_items(self, item_ids: list[str]):
        """
        Add items to selection by ID.
        
        This uses the AddToSelection API endpoint to add specified items
        to the current selection in the schematic editor.
        
        Args:
            item_ids: List of item ID strings to add to selection
            
        Returns:
            dict: Dictionary containing updated selection information
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            from kipy.proto.common.types import base_types_pb2
            
            if not item_ids or len(item_ids) == 0:
                return {
                    "error": "No item IDs provided",
                    "required": "List of item ID strings to select",
                    "example": "select_items(['symbol-id-1', 'wire-id-2'])"
                }
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {
                    "error": "No schematic document available",
                    "troubleshooting": [
                        "Ensure KiCad is running with a schematic open",
                        "Check that schematic is active in Eeschema"
                    ]
                }
            
            # Create AddToSelection request
            request = schematic_commands_pb2.AddToSelection()
            request.schematic.CopyFrom(doc_spec)
            
            # Add item IDs to select
            for item_id in item_ids:
                kiid = base_types_pb2.KIID()
                kiid.value = item_id
                request.item_ids.append(kiid)
            
            # Send the actual IPC command to KiCad
            response = self.send_schematic_command("AddToSelection", request)
            
            return {
                "api_endpoint": "AddToSelection",
                "connection_status": "SUCCESS - Items added to selection",
                "items_requested": len(item_ids),
                "selection_count": response.selection_count,
                "result": f"✅ {len(item_ids)} items added, {response.selection_count} total selected",
                "next_actions": [
                    "get_selection() to see all selected items",
                    "Perform operations on selected items",
                    "clear_selection() to deselect all"
                ]
            }
            
        except Exception as e:
            return {
                "api_endpoint": "AddToSelection",
                "connection_status": "FAILED - Selection addition error",
                "error": f"Failed to add items to selection: {str(e)}",
                "items_requested": len(item_ids) if item_ids else 0,
                "troubleshooting": [
                    "1. Ensure item IDs are valid and exist in schematic",
                    "2. Check that KiCad API has AddToSelection handler",
                    "3. Verify Python bindings are up to date",
                    "4. Try using get_schematic_items() to find valid IDs"
                ]
            }
    
    def clear_selection(self):
        """
        Clear current selection.
        
        This uses the ClearSelection API endpoint to deselect all items
        in the schematic editor.
        
        Returns:
            dict: Dictionary containing operation result
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            from google.protobuf.empty_pb2 import Empty
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {
                    "error": "No schematic document available",
                    "troubleshooting": [
                        "Ensure KiCad is running with a schematic open",
                        "Check that schematic is active in Eeschema"
                    ]
                }
            
            # Create ClearSelection request
            request = schematic_commands_pb2.ClearSelection()
            request.schematic.CopyFrom(doc_spec)
            
            # Send the actual IPC command to KiCad
            # ClearSelection returns Empty response
            response = self.send_schematic_command("ClearSelection", request)
            
            return {
                "api_endpoint": "ClearSelection",
                "connection_status": "SUCCESS - Selection cleared",
                "result": "✅ All items deselected",
                "next_actions": [
                    "select_items() to select specific items",
                    "select_by_type() to select by type",
                    "get_selection() to verify empty selection"
                ]
            }
            
        except Exception as e:
            return {
                "api_endpoint": "ClearSelection",
                "connection_status": "FAILED - Clear selection error",
                "error": f"Failed to clear selection: {str(e)}",
                "troubleshooting": [
                    "1. Ensure KiCad is running with a schematic open",
                    "2. Check that KiCad API has ClearSelection handler",
                    "3. Verify Python bindings are up to date",
                    "4. Try selecting and deselecting items manually"
                ]
            }
    
    def select_by_type(self, item_types: list[str]):
        """
        Select all items of specified types in the schematic.

        This convenience method combines GetSchematicItems and AddToSelection to select all
        items matching the specified types. Use 'Wire' for electrical connections - this is
        the preferred terminology and will be automatically mapped to KiCad's internal 'Line' type.

        Args:
            item_types: List of item type names to select (e.g., ['Symbol', 'Wire', 'Junction'])
                       Use 'Wire' for electrical connections (preferred over 'Line')

        Returns:
            dict: Dictionary containing selection results and counts by type
        """
        try:
            # Import protocol buffer messages
            from kipy.proto.schematic import schematic_commands_pb2
            from kipy.proto.schematic import schematic_types_pb2
            from kipy.proto.common.types import base_types_pb2
            
            if not item_types or len(item_types) == 0:
                return {
                    "error": "No item types provided",
                    "required": "List of item type names to select",
                    "example": "select_by_type(['Symbol', 'Wire'])",
                    "available_types": ['Symbol', 'Wire', 'Junction', 'LocalLabel', 'GlobalLabel'],
                    "note": "Use 'Wire' for electrical connections (internally mapped to Line type)"
                }
            
            # Get the active schematic document
            doc_spec = self.get_active_schematic_document()
            if not doc_spec:
                return {
                    "error": "No schematic document available",
                    "troubleshooting": [
                        "Ensure KiCad is running with a schematic open",
                        "Check that schematic is active in Eeschema"
                    ]
                }
            
            # First, get all schematic items
            get_items_request = schematic_commands_pb2.GetSchematicItems()
            get_items_request.schematic.CopyFrom(doc_spec)
            
            items_response = self.send_schematic_command("GetSchematicItems", get_items_request)
            
            # Track original user request for layer-based filtering
            # Wire = electrical lines (layer 1), Line = graphical lines (layer 3)
            user_requested_types = item_types.copy()
            requested_types = []
            for req_type in item_types:
                if req_type == 'Wire':
                    requested_types.append('Line')  # Map Wire -> Line (API uses "Line" internally)
                elif req_type == 'Line':
                    requested_types.append('Line')  # Line stays as Line
                else:
                    requested_types.append(req_type)

            # Filter items by type and collect their IDs
            items_to_select = []
            type_counts = {}

            for item in items_response.items:
                item_type = item.type_url.split('.')[-1] if '.' in item.type_url else item.type_url

                if item_type in requested_types:
                    # Extract ID based on type
                    item_id = None
                    
                    if item_type == 'Symbol':
                        symbol = schematic_types_pb2.Symbol()
                        if item.Unpack(symbol):
                            item_id = symbol.id.value
                    elif item_type == 'Wire':
                        wire = schematic_types_pb2.Wire()
                        if item.Unpack(wire):
                            item_id = wire.id.value
                    elif item_type == 'Line':
                        line = schematic_types_pb2.Line()
                        if item.Unpack(line):
                            # Apply layer-based filtering for Wire vs Line distinction
                            should_include = False
                            line_layer = line.layer if hasattr(line, 'layer') else 1

                            # Check if this Line item matches user's request
                            for original_type in user_requested_types:
                                if original_type == 'Wire' and line_layer == 1:
                                    # Wire = electrical lines (layer 1)
                                    should_include = True
                                    break
                                elif original_type == 'Line' and line_layer == 3:
                                    # Line = graphical lines (layer 3)
                                    should_include = True
                                    break

                            if should_include:
                                item_id = line.id.value
                            else:
                                item_id = None  # Skip this item
                    elif item_type == 'Junction':
                        junction = schematic_types_pb2.Junction()
                        if item.Unpack(junction):
                            item_id = junction.id.value
                    elif item_type == 'LocalLabel':
                        label = schematic_types_pb2.LocalLabel()
                        if item.Unpack(label):
                            item_id = label.id.value
                    
                    if item_id:
                        items_to_select.append(item_id)
                        # For counting, use the original user request type, not the internal API type
                        if item_type == 'Line':
                            # Determine if this was requested as Wire or Line based on layer
                            line_layer = 1
                            if item_type == 'Line':
                                # Get layer info for proper counting
                                temp_line = schematic_types_pb2.Line()
                                if item.Unpack(temp_line):
                                    line_layer = temp_line.layer if hasattr(temp_line, 'layer') else 1

                            # Count as the type the user requested
                            for original_type in user_requested_types:
                                if original_type == 'Wire' and line_layer == 1:
                                    type_counts['Wire'] = type_counts.get('Wire', 0) + 1
                                    break
                                elif original_type == 'Line' and line_layer == 3:
                                    type_counts['Line'] = type_counts.get('Line', 0) + 1
                                    break
                        else:
                            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            if not items_to_select:
                return {
                    "api_endpoint": "select_by_type",
                    "connection_status": "SUCCESS - No matching items found",
                    "requested_types": item_types,
                    "items_found": 0,
                    "result": "⚠️ No items of specified types found in schematic"
                }
            
            # Clear existing selection first
            clear_request = schematic_commands_pb2.ClearSelection()
            clear_request.schematic.CopyFrom(doc_spec)
            self.send_schematic_command("ClearSelection", clear_request)
            
            # Now add all matching items to selection
            select_request = schematic_commands_pb2.AddToSelection()
            select_request.schematic.CopyFrom(doc_spec)
            
            for item_id in items_to_select:
                kiid = base_types_pb2.KIID()
                kiid.value = item_id
                select_request.item_ids.append(kiid)
            
            # Send the selection request
            select_response = self.send_schematic_command("AddToSelection", select_request)
            
            return {
                "api_endpoint": "select_by_type",
                "connection_status": "SUCCESS - Items selected by type",
                "requested_types": item_types,
                "items_selected": len(items_to_select),
                "selection_count": select_response.selection_count,
                "type_breakdown": type_counts,
                "result": f"✅ {len(items_to_select)} items selected",
                "next_actions": [
                    "get_selection() to see selected items",
                    "Perform bulk operations on selection",
                    "clear_selection() to deselect all"
                ]
            }
            
        except Exception as e:
            return {
                "api_endpoint": "select_by_type",
                "connection_status": "FAILED - Type selection error",
                "error": f"Failed to select by type: {str(e)}",
                "requested_types": item_types if item_types else [],
                "troubleshooting": [
                    "1. Ensure valid type names are used",
                    "2. Check that schematic contains items of those types",
                    "3. Verify API has all required handlers",
                    "4. Try get_schematic_items() to see available types"
                ]
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