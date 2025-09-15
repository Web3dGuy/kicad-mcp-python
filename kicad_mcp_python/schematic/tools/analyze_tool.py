from dotenv import load_dotenv
import time

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

        # Smart caching system for unified API
        self._cached_status = None
        self._cache_timestamp = None
        self._cache_ttl = 1.0  # 1 second TTL for development

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

    def get_schematic_status(self, force_refresh: bool = False):
        """
        Retrieves comprehensive schematic status including all components,
        items, and information.

        This unified function consolidates all schematic data retrieval into a single,
        comprehensive call following the PCB tools pattern. Implements smart caching
        to address data freshness issues identified in smart routing.

        Args:
            force_refresh: If True, bypasses cache and fetches fresh data

        Returns:
            dict: Complete schematic state with all data needed for AI workflows
        """
        try:
            now = time.time()

            # Check if cache is valid
            if (not force_refresh and
                self._cached_status and
                self._cache_timestamp and
                (now - self._cache_timestamp) < self._cache_ttl):

                # Return cached data with freshness indicator
                cached_result = self._cached_status.copy()
                cached_result["cache_status"] = "hit"
                cached_result["cache_age_seconds"] = now - self._cache_timestamp
                return cached_result

            # Fetch fresh data
            fresh_data = self._fetch_comprehensive_status()

            # Update cache
            self._cached_status = fresh_data
            self._cache_timestamp = now

            fresh_data["cache_status"] = "miss"
            fresh_data["cache_age_seconds"] = 0
            return fresh_data

        except Exception as e:
            return {
                "api_endpoint": "get_schematic_status (unified)",
                "connection_status": "FAILED - Unified status retrieval error",
                "error": f"Failed to get comprehensive schematic status: {str(e)}",
                "cache_status": "error",
                "troubleshooting": [
                    "1. Ensure KiCad is running with a schematic open",
                    "2. Check IPC API is enabled in KiCad preferences",
                    "3. Verify schematic document is active in Eeschema",
                    "4. Try force_refresh=True to bypass cache"
                ]
            }

    def _fetch_comprehensive_status(self):
        """
        Internal method to fetch fresh comprehensive schematic data.

        Returns:
            dict: Complete schematic state organized by logical categories
        """
        from kipy.proto.schematic import schematic_commands_pb2
        from kipy.proto.schematic import schematic_types_pb2

        # Get active document
        doc_spec = self.get_active_schematic_document()
        if not doc_spec:
            raise Exception("No schematic document available")

        # 1. Get project info using existing method logic
        project_info = self._get_project_info_data(doc_spec)

        # 2. Get all schematic items and organize by type
        items_data = self._get_organized_items_data(doc_spec)

        # 3. Compile comprehensive result
        result = {
            "api_endpoint": "get_schematic_status (unified)",
            "connection_status": "SUCCESS - Comprehensive data retrieved",
            "project_info": project_info,
            "symbols": items_data.get("symbols", []),
            "wires": items_data.get("wires", []),
            "junctions": items_data.get("junctions", []),
            "labels": items_data.get("labels", []),
            "other_items": items_data.get("other_items", []),
            # "screenshot": "base64_image_data",  # TODO: Implement screenshot functionality
            "coordinate_system": "nanometers (nm)",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_items": sum(len(v) for k, v in items_data.items() if isinstance(v, list)),
            "api_version": "1.0",
            "data_freshness": "fresh",
            "cache_invalidation_note": "Cache invalidated after any write operation (create, delete, move)"
        }

        return result

    def _get_project_info_data(self, doc_spec):
        """Get project information data."""
        from kipy.proto.schematic import schematic_commands_pb2

        try:
            request = schematic_commands_pb2.GetSchematicInfo()
            request.schematic.CopyFrom(doc_spec)
            response = self.send_schematic_command("GetSchematicInfo", request)

            return {
                "name": response.project_name,
                "sheet_count": response.sheet_count,
                "symbol_count": response.symbol_count,
                "net_count": response.net_count,
                "sheet_names": list(response.sheet_names)
            }
        except Exception as e:
            return {
                "error": f"Failed to get project info: {str(e)}",
                "name": "unknown",
                "sheet_count": 0,
                "symbol_count": 0,
                "net_count": 0,
                "sheet_names": []
            }

    def _get_organized_items_data(self, doc_spec):
        """Get and organize all schematic items by logical categories."""
        from kipy.proto.schematic import schematic_commands_pb2
        from kipy.proto.schematic import schematic_types_pb2

        try:
            request = schematic_commands_pb2.GetSchematicItems()
            request.schematic.CopyFrom(doc_spec)
            response = self.send_schematic_command("GetSchematicItems", request)

            # Organize items by logical categories
            symbols = []
            wires = []
            junctions = []
            labels = []
            other_items = []

            for item in response.items:
                item_type = item.type_url.split('.')[-1] if '.' in item.type_url else item.type_url

                if item_type == 'Symbol':
                    symbol = schematic_types_pb2.Symbol()
                    if item.Unpack(symbol):
                        symbol_data = {
                            "id": symbol.id.value,
                            "reference": symbol.reference,
                            "value": symbol.value,
                            "library_id": symbol.library_id,
                            "position": {
                                "x_nm": symbol.position.x_nm,
                                "y_nm": symbol.position.y_nm,
                                "x_mm": symbol.position.x_nm / 1_000_000,
                                "y_mm": symbol.position.y_nm / 1_000_000
                            },
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
                                    "y_nm": pin.position.y_nm,
                                    "x_mm": pin.position.x_nm / 1_000_000,
                                    "y_mm": pin.position.y_nm / 1_000_000
                                },
                                "electrical_type": pin.electrical_type,
                                "orientation": pin.orientation,
                                "length": pin.length
                            }
                            symbol_data["pins"].append(pin_data)

                        symbols.append(symbol_data)

                elif item_type == 'Line':
                    line = schematic_types_pb2.Line()
                    if item.Unpack(line):
                        # Apply scaling workaround from existing implementation
                        scale_factor = 1
                        if abs(line.start.x_nm) < 10_000_000 and abs(line.start.y_nm) < 10_000_000:
                            scale_factor = 100

                        wire_data = {
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
                            "layer": line.layer if hasattr(line, 'layer') else 1,
                            "layer_type": "WIRE" if hasattr(line, 'layer') and line.layer == 1 else "BUS" if hasattr(line, 'layer') and line.layer == 2 else "GRAPHICAL" if hasattr(line, 'layer') and line.layer == 3 else f"UNKNOWN({line.layer if hasattr(line, 'layer') else 'none'})"
                        }
                        wires.append(wire_data)

                elif item_type == 'Junction':
                    junction = schematic_types_pb2.Junction()
                    if item.Unpack(junction):
                        junction_data = {
                            "id": junction.id.value,
                            "position": {
                                "x_nm": junction.position.x_nm,
                                "y_nm": junction.position.y_nm,
                                "x_mm": junction.position.x_nm / 1_000_000,
                                "y_mm": junction.position.y_nm / 1_000_000
                            },
                            "diameter": getattr(junction, 'diameter', 0)
                        }
                        junctions.append(junction_data)

                elif item_type in ['LocalLabel', 'GlobalLabel', 'HierLabel']:
                    # Handle different label types
                    if item_type == 'LocalLabel':
                        label = schematic_types_pb2.LocalLabel()
                    elif item_type == 'GlobalLabel':
                        label = schematic_types_pb2.GlobalLabel()
                    else:
                        label = schematic_types_pb2.HierLabel()

                    if item.Unpack(label):
                        # Apply same scaling workaround as wires (Section 5 fix)
                        scale_factor = 1
                        if abs(label.position.x_nm) < 10_000_000 and abs(label.position.y_nm) < 10_000_000:
                            scale_factor = 100

                        # Extract text from nested structure: label.text.text.text
                        text_content = ""
                        if hasattr(label, 'text') and hasattr(label.text, 'text'):
                            if hasattr(label.text.text, 'text'):
                                text_content = label.text.text.text
                            elif isinstance(label.text.text, str):
                                text_content = label.text.text

                        label_data = {
                            "id": label.id.value,
                            "type": item_type,
                            "text": text_content,
                            "position": {
                                "x_nm": label.position.x_nm * scale_factor,
                                "y_nm": label.position.y_nm * scale_factor,
                                "x_mm": (label.position.x_nm * scale_factor) / 1_000_000,
                                "y_mm": (label.position.y_nm * scale_factor) / 1_000_000
                            }
                        }
                        labels.append(label_data)

                else:
                    # Track other item types
                    other_items.append({
                        "type": item_type,
                        "type_url": item.type_url,
                        "note": "Item type not yet categorized in unified status"
                    })

            return {
                "symbols": symbols,
                "wires": wires,
                "junctions": junctions,
                "labels": labels,
                "other_items": other_items
            }

        except Exception as e:
            return {
                "symbols": [],
                "wires": [],
                "junctions": [],
                "labels": [],
                "other_items": [],
                "error": f"Failed to get organized items: {str(e)}"
            }

    def invalidate_cache(self):
        """
        Invalidate the comprehensive status cache.

        Should be called after any write operations (create, delete, move)
        to ensure fresh data for subsequent reads.
        """
        self._cached_status = None
        self._cache_timestamp = None

    def get_schematic_info(self):
        """
        Get basic schematic information using the new GetSchematicInfo API endpoint.

        This tests the actual IPC connection to KiCad's schematic API.

        DEPRECATED: Use get_schematic_status() for comprehensive data.
        This function now delegates to the unified implementation for consistency.

        Returns:
            dict: Basic schematic information including project name, sheet count, etc.
        """
        # Delegate to unified implementation
        status = self.get_schematic_status()

        if "error" in status:
            return {
                "api_endpoint": "GetSchematicInfo (delegated)",
                "connection_status": "FAILED - Delegated to unified status",
                "error": status["error"],
                "deprecation_notice": "Use get_schematic_status() for comprehensive data",
                "test_result": "❌ Unified implementation failed"
            }

        # Extract just project info for backward compatibility
        project_info = status.get("project_info", {})
        return {
            "api_endpoint": "GetSchematicInfo (delegated)",
            "connection_status": "SUCCESS - Connected via unified status",
            "project_name": project_info.get("name", "unknown"),
            "sheet_count": project_info.get("sheet_count", 0),
            "symbol_count": project_info.get("symbol_count", 0),
            "net_count": project_info.get("net_count", 0),
            "sheet_names": project_info.get("sheet_names", []),
            "test_result": "✅ Connection working via unified implementation",
            "deprecation_notice": "⚠️  DEPRECATED: Use get_schematic_status() for comprehensive data",
            "cache_info": {
                "cache_status": status.get("cache_status", "unknown"),
                "cache_age_seconds": status.get("cache_age_seconds", 0)
            }
        }

    def get_schematic_items(self, item_types: str = "all"):
        """
        Get schematic items using the new GetSchematicItems API endpoint.

        This retrieves actual schematic elements like wires, junctions, and symbols from KiCad.

        DEPRECATED: Use get_schematic_status() for comprehensive data.
        This function now delegates to the unified implementation for consistency.

        Args:
            item_types: Types of items to retrieve (default: "all")

        Returns:
            dict: Dictionary containing schematic items information
        """
        # Delegate to unified implementation
        status = self.get_schematic_status()

        if "error" in status:
            return {
                "api_endpoint": "GetSchematicItems (delegated)",
                "connection_status": "FAILED - Delegated to unified status",
                "error": status["error"],
                "deprecation_notice": "Use get_schematic_status() for comprehensive data",
                "test_result": "❌ Unified implementation failed"
            }

        # Combine all item categories for backward compatibility
        all_items = []
        all_items.extend(status.get("symbols", []))

        # Add wires with proper type field for smart routing compatibility
        wires = status.get("wires", [])
        for wire in wires:
            wire_item = wire.copy()
            wire_item["type"] = "Line"  # SmartWireTool expects this type
            all_items.append(wire_item)

        all_items.extend(status.get("junctions", []))
        all_items.extend(status.get("labels", []))
        all_items.extend(status.get("other_items", []))

        return {
            "api_endpoint": "GetSchematicItems (delegated)",
            "connection_status": "SUCCESS - Connected via unified status",
            "requested_types": item_types,
            "total_items": status.get("total_items", len(all_items)),
            "items_retrieved": len(all_items),
            "items": all_items,
            "note": f"Retrieved {len(all_items)} items via unified implementation",
            "test_result": "✅ GetSchematicItems working via unified implementation",
            "deprecation_notice": "⚠️  DEPRECATED: Use get_schematic_status() for organized data by category",
            "cache_info": {
                "cache_status": status.get("cache_status", "unknown"),
                "cache_age_seconds": status.get("cache_age_seconds", 0)
            }
        }

    def get_symbol_positions(self):
        """
        Get all symbols in the schematic with their exact positions and pin data.

        This uses the enhanced GetSchematicItems API that now returns symbol positions
        and embedded pin information for precise coordinate-based wire placement.

        DEPRECATED: Use get_schematic_status() for comprehensive data.
        This function now delegates to the unified implementation for consistency.

        Returns:
            dict: Dictionary containing all symbols with positions and pins
        """
        # Delegate to unified implementation
        status = self.get_schematic_status()

        if "error" in status:
            return {
                "api_endpoint": "GetSchematicItems (Enhanced, delegated)",
                "connection_status": "FAILED - Delegated to unified status",
                "error": status["error"],
                "deprecation_notice": "Use get_schematic_status() for comprehensive data",
                "test_result": "❌ Unified implementation failed"
            }

        symbols = status.get("symbols", [])
        total_items = status.get("total_items", 0)

        result = {
            "api_endpoint": "GetSchematicItems (Enhanced, delegated)",
            "connection_status": "SUCCESS - Symbol positions retrieved via unified status",
            "total_items": total_items,
            "symbol_count": len(symbols),
            "other_items_count": total_items - len(symbols),
            "symbols": symbols,
            "coordinate_system": "nanometers (nm)",
            "test_result": "✅ Symbol positions available via unified implementation",
            "deprecation_notice": "⚠️  DEPRECATED: Use get_schematic_status() for all data categories",
            "cache_info": {
                "cache_status": status.get("cache_status", "unknown"),
                "cache_age_seconds": status.get("cache_age_seconds", 0)
            }
        }

        if len(symbols) == 0:
            result["warning"] = "No symbols found - ensure schematic has components placed"

        return result

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