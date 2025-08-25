from typing import Dict

from ..schematicmodule import SchematicTool
from ...core.ActionFlowManager import ActionFlowManager
from ...core.mcp_manager import ToolManager

from mcp.server.fastmcp import FastMCP


class SchematicManipulator(ToolManager, SchematicTool):
    """
    A class that provides tools for manipulating schematic elements.
    This follows the same multi-step pattern as PCB manipulation tools.
    """

    def __init__(self, mcp: FastMCP):
        super().__init__(mcp)
        
        # Create schematic items workflow (proof of concept)
        self.add_tool(self.create_schematic_item_step_1)
        self.add_tool(self.create_schematic_item_step_2) 
        self.add_tool(self.create_schematic_item_step_3)
        
        # Draw wire workflow (Phase 1A implementation)
        self.add_tool(self.draw_wire_step_1)
        self.add_tool(self.draw_wire_step_2)
        self.add_tool(self.draw_wire_step_3)

    def create_schematic_item_step_1(self):
        """
        Entrance tool to create a new schematic item (junction, wire, label, etc.).
        This function serves as an entry point and acts like --help before directly using the schematic API.
        
        Returns:
            dict: Available schematic item types that can be created
            
        Next action:
            create_schematic_item_step_2
        """
        return {
            "workflow": "Create Schematic Item - Step 1 of 3",
            "description": "Select the type of schematic item to create",
            "available_types": {
                "Junction": "Connection point for wires",
                "Wire": "Electrical wire connection",
                "Bus": "Bus segment for multiple signals", 
                "LocalLabel": "Local net label",
                "GlobalLabel": "Global net label",
                "Line": "Graphical line (non-electrical)",
                "Text": "Text annotation"
            },
            "api_endpoint": "Uses CreateSchematicItems endpoint",
            "next_step": "Call create_schematic_item_step_2(item_type) with your chosen type",
            "example": "create_schematic_item_step_2('Junction')"
        }

    def create_schematic_item_step_2(self, item_type: str):
        """
        Returns the configuration parameters required for creating the specified schematic item type.
        
        Args:
            item_type (str): The schematic item type (e.g., 'Junction', 'Wire', 'LocalLabel')
        
        Returns: 
            dict: Configuration parameters and data types required to create the item
            
        Next action:
            create_schematic_item_step_3
        """
        
        # Define the parameters for each schematic item type
        item_configs = {
            "Junction": {
                "description": "Wire junction (connection point)",
                "required_parameters": {
                    "position": "Vector2 - Position in nanometers (x_nm, y_nm)",
                    "diameter": "int32 - Junction diameter in nanometers"
                },
                "optional_parameters": {
                    "color": "Color - Junction color (optional)"
                },
                "example": {
                    "position": {"x_nm": 50800000, "y_nm": 50800000},  # 50.8mm
                    "diameter": 400000  # 0.4mm
                }
            },
            "Wire": {
                "description": "Electrical wire segment",
                "required_parameters": {
                    "start": "Vector2 - Start position in nanometers",
                    "end": "Vector2 - End position in nanometers"
                },
                "optional_parameters": {
                    "stroke": "StrokeAttributes - Line style and width"
                },
                "example": {
                    "start": {"x_nm": 50800000, "y_nm": 50800000},
                    "end": {"x_nm": 76200000, "y_nm": 50800000}  # 25.4mm horizontal
                }
            },
            "Bus": {
                "description": "Bus segment for multiple signals",
                "required_parameters": {
                    "start": "Vector2 - Start position in nanometers", 
                    "end": "Vector2 - End position in nanometers"
                },
                "optional_parameters": {
                    "stroke": "StrokeAttributes - Line style and width"
                },
                "example": {
                    "start": {"x_nm": 50800000, "y_nm": 50800000},
                    "end": {"x_nm": 50800000, "y_nm": 76200000}  # 25.4mm vertical
                }
            },
            "LocalLabel": {
                "description": "Local net label",
                "required_parameters": {
                    "position": "Vector2 - Position in nanometers",
                    "text": "Text - Label text content"
                },
                "optional_parameters": {},
                "example": {
                    "position": {"x_nm": 50800000, "y_nm": 50800000},
                    "text": {"text": "VCC"}
                }
            },
            "GlobalLabel": {
                "description": "Global net label", 
                "required_parameters": {
                    "position": "Vector2 - Position in nanometers",
                    "text": "Text - Label text content"
                },
                "optional_parameters": {},
                "example": {
                    "position": {"x_nm": 50800000, "y_nm": 50800000},
                    "text": {"text": "RESET"}
                }
            }
        }
        
        if item_type not in item_configs:
            return {
                "error": f"Unsupported item type: {item_type}",
                "supported_types": list(item_configs.keys()),
                "suggestion": "Use create_schematic_item_step_1() to see all available types"
            }
        
        config = item_configs[item_type]
        return {
            "workflow": f"Create Schematic Item - Step 2 of 3",
            "item_type": item_type,
            "description": config["description"],
            "required_parameters": config["required_parameters"],
            "optional_parameters": config["optional_parameters"],
            "example": config["example"],
            "next_step": f"Call create_schematic_item_step_3('{item_type}', args) with your parameters",
            "api_endpoint": "CreateSchematicItems"
        }

    def create_schematic_item_step_3(self, item_type: str, args: dict):
        """
        Creates the schematic item with the specified type and arguments.
        
        Args:
            item_type (str): The schematic item type (e.g., 'Junction', 'Wire', 'LocalLabel')
            args (dict): The parameters required to create the item
        
        Returns:
            dict: Result of the creation operation
            
        Next action:
            get_schematic_status (to verify the creation)
        """
        try:
            # This would use the CreateSchematicItems API endpoint
            # For the proof of concept, we validate the arguments and show what would be created
            
            result = {
                "workflow": "Create Schematic Item - Step 3 of 3",
                "operation": "CreateSchematicItems API call",
                "item_type": item_type,
                "provided_args": args,
                "status": "proof_of_concept",
                "message": f"Would create {item_type} with provided parameters",
                "api_integration": "Ready - Protocol buffers generated and available",
                "next_steps": [
                    "Connect to running KiCad instance with schematic open",
                    "Enable IPC API server in KiCad",
                    "Call actual CreateSchematicItems endpoint",
                    "Verify creation with get_schematic_status"
                ]
            }
            
            # Validate that required parameters are provided
            if item_type == "Junction":
                if "position" not in args or "diameter" not in args:
                    result["validation_error"] = "Missing required parameters: position and diameter"
            elif item_type in ["Wire", "Bus"]: 
                if "start" not in args or "end" not in args:
                    result["validation_error"] = "Missing required parameters: start and end"
            elif item_type in ["LocalLabel", "GlobalLabel"]:
                if "position" not in args or "text" not in args:
                    result["validation_error"] = "Missing required parameters: position and text"
            
            return result
            
        except Exception as e:
            return {
                "error": f"Failed to create schematic item: {str(e)}",
                "item_type": item_type,
                "args": args
            }
    
    def draw_wire_step_1(self):
        """
        Entrance tool to draw a wire between two points in the schematic.
        This uses the new DrawWire API endpoint for direct wire creation.
        
        Returns:
            dict: Information about the DrawWire workflow
            
        Next action:
            draw_wire_step_2
        """
        return {
            "workflow": "Draw Wire - Step 1 of 3",
            "description": "Draw an electrical wire between two points",
            "purpose": "Creates a wire segment for electrical connections",
            "api_endpoint": "DrawWire (Phase 1A implementation)",
            "parameters_overview": {
                "start_point": "Starting position of the wire",
                "end_point": "Ending position of the wire",
                "width": "Optional wire width (default: 0 = use standard width)"
            },
            "coordinate_system": "Positions are in nanometers (1mm = 1,000,000 nm)",
            "next_step": "Call draw_wire_step_2() to see parameter details",
            "example": "draw_wire_step_2()"
        }
    
    def draw_wire_step_2(self):
        """
        Returns the parameter requirements for drawing a wire.
        
        Returns:
            dict: Parameter specifications for DrawWire
            
        Next action:
            draw_wire_step_3
        """
        return {
            "workflow": "Draw Wire - Step 2 of 3",
            "description": "Specify wire endpoints",
            "required_parameters": {
                "start_point": {
                    "type": "dict with x_nm and y_nm",
                    "description": "Starting position in nanometers",
                    "example": {"x_nm": 50800000, "y_nm": 50800000}  # 50.8mm, 50.8mm
                },
                "end_point": {
                    "type": "dict with x_nm and y_nm", 
                    "description": "Ending position in nanometers",
                    "example": {"x_nm": 101600000, "y_nm": 50800000}  # 101.6mm, 50.8mm
                }
            },
            "optional_parameters": {
                "width": {
                    "type": "int",
                    "description": "Wire width in nanometers (0 = default)",
                    "default": 0,
                    "example": 150000  # 0.15mm
                }
            },
            "grid_alignment": "Wires should align to schematic grid (typically 1.27mm / 1270000nm)",
            "next_step": "Call draw_wire_step_3(args) with your parameters",
            "example_call": "draw_wire_step_3({'start_point': {'x_nm': 50800000, 'y_nm': 50800000}, 'end_point': {'x_nm': 101600000, 'y_nm': 50800000}})"
        }
    
    def draw_wire_step_3(self, args: dict):
        """
        Draws a wire between the specified points using the DrawWire API.
        
        Args:
            args (dict): Wire parameters containing:
                - start_point: dict with x_nm and y_nm
                - end_point: dict with x_nm and y_nm
                - width (optional): wire width in nanometers
        
        Returns:
            dict: Result of the wire drawing operation
            
        Next action:
            get_schematic_status (to verify the wire was created)
        """
        try:
            # Validate required parameters
            if "start_point" not in args or "end_point" not in args:
                return {
                    "error": "Missing required parameters",
                    "required": ["start_point", "end_point"],
                    "provided": list(args.keys()),
                    "suggestion": "Use draw_wire_step_2() to see parameter requirements"
                }
            
            start = args["start_point"]
            end = args["end_point"]
            
            # Validate coordinate structure
            if not all(k in start for k in ["x_nm", "y_nm"]):
                return {
                    "error": "Invalid start_point structure",
                    "expected": {"x_nm": "integer", "y_nm": "integer"},
                    "provided": start
                }
            
            if not all(k in end for k in ["x_nm", "y_nm"]):
                return {
                    "error": "Invalid end_point structure",
                    "expected": {"x_nm": "integer", "y_nm": "integer"},
                    "provided": end
                }
            
            # Get wire width (optional)
            width = args.get("width", 0)
            
            # Call the DrawWire API
            from kipy.proto.schematic import schematic_commands_pb2
            from kipy.proto.common.types import base_types_pb2
            
            request = schematic_commands_pb2.DrawWire()
            
            # Set start point
            request.start_point.x_nm = start["x_nm"]
            request.start_point.y_nm = start["y_nm"]
            
            # Set end point
            request.end_point.x_nm = end["x_nm"]
            request.end_point.y_nm = end["y_nm"]
            
            # Set width if provided
            if width > 0:
                request.width = width
            
            # Get the schematic document specifier
            doc_spec = self.get_active_schematic_document()
            if doc_spec:
                request.schematic.CopyFrom(doc_spec)
            
            # Send the request to KiCad
            response = self.send_schematic_command("DrawWire", request)
            
            if response and hasattr(response, 'wire_id'):
                return {
                    "workflow": "Draw Wire - Step 3 of 3",
                    "status": "success",
                    "operation": "Wire created",
                    "wire_id": response.wire_id.value if response.wire_id.value else None,
                    "start_point": f"({start['x_nm']/1000000:.1f}mm, {start['y_nm']/1000000:.1f}mm)",
                    "end_point": f"({end['x_nm']/1000000:.1f}mm, {end['y_nm']/1000000:.1f}mm)",
                    "length_mm": ((end['x_nm'] - start['x_nm'])**2 + (end['y_nm'] - start['y_nm'])**2)**0.5 / 1000000,
                    "next_actions": [
                        "get_schematic_status() to verify wire creation",
                        "draw_wire_step_1() to draw another wire",
                        "break_wire_step_1() to break wire at junction (coming soon)"
                    ]
                }
            else:
                error_msg = response.error if response and hasattr(response, 'error') else "Unknown error"
                return {
                    "workflow": "Draw Wire - Step 3 of 3",
                    "status": "failed",
                    "error": error_msg,
                    "troubleshooting": [
                        "Ensure KiCad is running with a schematic open",
                        "Verify IPC API server is enabled in KiCad",
                        "Check that coordinates are within schematic bounds",
                        "Ensure coordinates align to schematic grid"
                    ]
                }
                
        except ImportError as e:
            return {
                "error": "Failed to import protocol buffer modules",
                "details": str(e),
                "suggestion": "Ensure Python bindings have been generated (run kicad-python/build.py)"
            }
        except Exception as e:
            return {
                "error": f"Failed to draw wire: {str(e)}",
                "args": args,
                "suggestion": "Check KiCad connection and try again"
            }


class SchematicManipulationTools:
    """
    Tool collection for schematic manipulation operations.
    """
    
    @staticmethod
    def register_tools(mcp: FastMCP):
        """
        Register all schematic manipulation tools with the MCP server.
        
        Args:
            mcp: FastMCP server instance
        """
        SchematicManipulator(mcp)