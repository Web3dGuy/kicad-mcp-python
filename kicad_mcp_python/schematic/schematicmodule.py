from mcp.server.fastmcp import FastMCP
from kipy import KiCad
from kipy.proto.common.types import base_types_pb2
from kipy.proto.common.types.base_types_pb2 import DocumentType
from kipy.proto.schematic import schematic_commands_pb2

class SchematicTool:
    """
    Represents a schematic module with its properties and methods.
    """

    def initialize_kicad(self):
        """
        Initialize KiCad IPC connection for schematic operations.
        """
        try:
            # Initialize the KiCad client with IPC connection
            # Use 60-second timeout to handle comprehensive library loading (like UI)
            self.kicad = KiCad(timeout_ms=60000)
            # Test connection with a ping
            self.kicad.ping()
            print(f"Successfully connected to KiCad IPC server")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize KiCad for schematic operations: {str(e)}")
    
    def get_active_schematic_document(self):
        """
        Get the document specifier for the active schematic.
        
        Returns:
            DocumentSpecifier for the current schematic, or None if unavailable
        """
        try:
            if not hasattr(self, 'kicad'):
                self.initialize_kicad()
            
            # Get open schematic documents from KiCad
            docs = self.kicad.get_open_documents(DocumentType.DOCTYPE_SCHEMATIC)
            if len(docs) > 0:
                print(f"Found {len(docs)} open schematic document(s)")
                return docs[0]  # Return the first open schematic
            else:
                print("Warning: No schematic documents are open in KiCad")
                return None  # Don't create fake document specifier
        except Exception as e:
            print(f"Warning: Could not get schematic document specifier: {e}")
            return None
    
    def send_schematic_command(self, command_name: str, request):
        """
        Send a command to the KiCad schematic API using the proper IPC client.
        
        Args:
            command_name: Name of the command (e.g., "DrawWire")
            request: Protocol buffer request object
            
        Returns:
            Response from KiCad API
        """
        try:
            if not hasattr(self, 'kicad'):
                self.initialize_kicad()
            
            # Use the KiCad client's send method with the proper response type
            if command_name == "DrawWire":
                response = self.kicad._client.send(request, schematic_commands_pb2.DrawWireResponse)
                return response
            elif command_name == "GetSchematicInfo":
                response = self.kicad._client.send(request, schematic_commands_pb2.SchematicInfoResponse)
                return response
            elif command_name == "GetSchematicItems":
                response = self.kicad._client.send(request, schematic_commands_pb2.GetSchematicItemsResponse)
                return response
            elif command_name == "CreateSchematicItems":
                response = self.kicad._client.send(request, schematic_commands_pb2.CreateSchematicItemsResponse)
                return response
            elif command_name == "GetSymbolPins":
                response = self.kicad._client.send(request, schematic_commands_pb2.GetSymbolPinsResponse)
                return response
            elif command_name == "GetComponentBounds":
                response = self.kicad._client.send(request, schematic_commands_pb2.GetComponentBoundsResponse)
                return response
            elif command_name == "GetGridAnchors":
                response = self.kicad._client.send(request, schematic_commands_pb2.GetGridAnchorsResponse)
                return response
            elif command_name == "GetConnectionPoints":
                response = self.kicad._client.send(request, schematic_commands_pb2.GetConnectionPointsResponse)
                return response
            # Selection Management System - Phase 1 Foundational Optimizations
            elif command_name == "GetSelection":
                response = self.kicad._client.send(request, schematic_commands_pb2.SelectionResponse)
                return response
            elif command_name == "AddToSelection":
                response = self.kicad._client.send(request, schematic_commands_pb2.SelectionResponse)
                return response
            elif command_name == "RemoveFromSelection":
                response = self.kicad._client.send(request, schematic_commands_pb2.SelectionResponse)
                return response
            elif command_name == "ClearSelection":
                from google.protobuf.empty_pb2 import Empty
                response = self.kicad._client.send(request, Empty)
                return response
            # Symbol Placement System - Phase 2 Symbol Placement
            elif command_name == "PlaceSymbol":
                response = self.kicad._client.send(request, schematic_commands_pb2.PlaceSymbolResponse)
                return response
            elif command_name == "GetSymbolLibraries":
                response = self.kicad._client.send(request, schematic_commands_pb2.GetSymbolLibrariesResponse)
                return response
            elif command_name == "SearchSymbols":
                response = self.kicad._client.send(request, schematic_commands_pb2.SearchSymbolsResponse)
                return response
            elif command_name == "PreloadSymbolLibraries":
                response = self.kicad._client.send(request, schematic_commands_pb2.PreloadSymbolLibrariesResponse)
                return response
            elif command_name == "GetLibraryLoadStatus":
                response = self.kicad._client.send(request, schematic_commands_pb2.GetLibraryLoadStatusResponse)
                return response
            elif command_name == "RefreshSymbolLibraries":
                response = self.kicad._client.send(request, schematic_commands_pb2.RefreshSymbolLibrariesResponse)
                return response
            else:
                raise ValueError(f"Unsupported schematic command: {command_name}")
                
        except Exception as e:
            print(f"Error sending schematic command {command_name}: {e}")
            # Don't return mock responses - let the error propagate to show real connection issues
            raise e
    
    def send_editor_command(self, command_name: str, request):
        """
        Send a command to the KiCad editor API using the proper IPC client.
        
        Args:
            command_name: Name of the command (e.g., "SaveDocument", "DeleteItems") 
            request: Protocol buffer request object
            
        Returns:
            Response from KiCad API
        """
        try:
            if not hasattr(self, 'kicad'):
                self.initialize_kicad()
            
            # Import editor command response types
            from kipy.proto.common.commands import editor_commands_pb2
            from google.protobuf.empty_pb2 import Empty
            
            # Use the KiCad client's send method with the proper response type
            if command_name == "SaveDocument":
                # SaveDocument returns Empty response type
                response = self.kicad._client.send(request, Empty)  
                return response
            elif command_name == "DeleteItems":
                response = self.kicad._client.send(request, editor_commands_pb2.DeleteItemsResponse)
                return response
            else:
                raise ValueError(f"Unsupported editor command: {command_name}")
                
        except Exception as e:
            print(f"Error sending editor command {command_name}: {e}")
            # Let the error propagate to show real connection issues
            raise e

    def manage_symbol_libraries(
        self,
        mode: str = "status",
        library_names: list[str] = [],
        force_reload: bool = False
    ) -> dict:
        """
        Unified symbol library management tool that matches KiCad UI behavior.

        This consolidates library loading, status checking, and refresh operations
        into a single tool that mirrors how KiCad's schematic editor works.

        Args:
            mode: Operation mode - "load", "status", or "refresh"
                - "load": Comprehensive library loading (like first symbol button press)
                - "status": Check which libraries are currently loaded
                - "refresh": Refresh externally modified libraries
            library_names: Specific libraries to target (empty = all libraries)
            force_reload: Force reload even if already loaded (optional, no artificial limits)

        Returns:
            Dictionary with operation results, statistics, and timing
        """
        try:
            if mode == "load":
                # Comprehensive loading - matches UI behavior when pressing symbol button first time
                request = schematic_commands_pb2.PreloadSymbolLibraries()
                for lib_name in library_names:
                    request.library_names.append(lib_name)
                request.force_reload = force_reload

                response = self.send_schematic_command("PreloadSymbolLibraries", request)

                result = {
                    "mode": "load",
                    "operation": "Comprehensive library loading (UI-matching behavior)",
                    "loaded_libraries": response.loaded_libraries,
                    "failed_libraries": list(response.failed_libraries),
                    "loading_time_seconds": response.loading_time_seconds,
                    "note": "No artificial limits - loads all libraries like KiCad UI (60-second timeout protection)"
                }

                if response.error:
                    result["error"] = response.error

                return result

            elif mode == "status":
                # Check current library loading status
                request = schematic_commands_pb2.GetLibraryLoadStatus()
                response = self.send_schematic_command("GetLibraryLoadStatus", request)

                return {
                    "mode": "status",
                    "operation": "Library loading status check",
                    "symbols_loaded": response.symbols_loaded,
                    "footprints_loaded": response.footprints_loaded,
                    "symbol_library_count": response.symbol_library_count,
                    "footprint_library_count": response.footprint_library_count,
                    "loaded_symbol_libraries": list(response.loaded_symbol_libraries)
                }

            elif mode == "refresh":
                # Refresh libraries to pick up external changes
                request = schematic_commands_pb2.RefreshSymbolLibraries()
                for lib_name in library_names:
                    request.library_names.append(lib_name)

                response = self.send_schematic_command("RefreshSymbolLibraries", request)

                result = {
                    "mode": "refresh",
                    "operation": "Library refresh for external changes",
                    "refreshed_libraries": response.refreshed_libraries,
                    "failed_libraries": list(response.failed_libraries),
                    "refresh_time_seconds": response.refresh_time_seconds
                }

                if response.error:
                    result["error"] = response.error

                return result

            else:
                return {"error": f"Invalid mode '{mode}'. Use 'load', 'status', or 'refresh'"}

        except Exception as e:
            return {"error": f"Failed to manage libraries (mode: {mode}): {e}"}