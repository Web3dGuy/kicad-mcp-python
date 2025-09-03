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
            self.kicad = KiCad()
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