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