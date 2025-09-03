"""
Smart Routing MCP Tool Integration

This module exposes our smart routing implementation as MCP tools that Claude can use
to create intelligent wire connections in KiCad schematics.
"""

from typing import Dict, List, Any, Optional
from ...tools.smart_wire_tool import SmartWireTool
from ..schematicmodule import SchematicTool
from ...core.mcp_manager import ToolManager
from mcp.server.fastmcp import FastMCP


class SchematicSmartRouter(ToolManager, SchematicTool):
    """
    MCP tool wrapper for smart wire routing functionality.
    
    This class exposes the smart routing algorithms we've implemented
    to enable AI-driven schematic design with professional routing patterns.
    """
    
    def __init__(self, mcp: FastMCP):
        super().__init__(mcp)
        
        # Initialize the smart wire tool
        self.smart_wire_tool = SmartWireTool()
        
        # Register smart routing workflow tools
        self.add_tool(self.smart_route_step_1)
        self.add_tool(self.smart_route_step_2)
        self.add_tool(self.smart_route_step_3)
        
        # Register analysis tools
        self.add_tool(self.analyze_routing_path)
        self.add_tool(self.preview_smart_route)
    
    def smart_route_step_1(self):
        """
        Step 1: Introduction to smart wire routing between pins.
        
        This tool implements intelligent Manhattan routing, pin approach angles,
        and component boundary awareness for professional PCB design patterns.
        
        Returns:
            Information about the smart routing workflow
            
        Next action:
            smart_route_step_2
        """
        return {
            "workflow": "Smart Wire Routing - Step 1 of 3",
            "description": "Intelligent wire routing with Manhattan paths and collision avoidance",
            "capabilities": {
                "manhattan_routing": "90-degree angle routing for clean schematics",
                "pin_awareness": "Optimal approach angles based on pin orientation",
                "component_avoidance": "Routes around component boundaries",
                "quality_scoring": "Evaluates path quality for professional standards"
            },
            "routing_modes": {
                "manhattan": "90-degree angles only (recommended)",
                "direct": "Straight line connection",
                "45_degree": "45-degree angle routing"
            },
            "prerequisites": "Must call get_symbol_positions() first to get symbol data",
            "next_step": "Call smart_route_step_2() to see required parameters",
            "example": "smart_route_step_2()"
        }
    
    def smart_route_step_2(self):
        """
        Step 2: Show required parameters for smart routing.
        
        Returns:
            Parameter specifications for smart routing
            
        Next action:
            smart_route_step_3
        """
        return {
            "workflow": "Smart Wire Routing - Step 2 of 3",
            "required_parameters": {
                "start_symbol_id": "UUID of the starting symbol",
                "start_pin_number": "Pin number on start symbol (e.g., '1', '2')",
                "end_symbol_id": "UUID of the ending symbol",
                "end_pin_number": "Pin number on end symbol",
                "symbols_data": "Complete symbol data from get_symbol_positions()"
            },
            "optional_parameters": {
                "routing_mode": "Routing algorithm: 'manhattan' (default), 'direct', '45_degree'"
            },
            "coordinate_system": "All positions in nanometers (1mm = 1,000,000 nm)",
            "next_step": "Call smart_route_step_3(args) with parameters",
            "example": {
                "command": "smart_route_step_3(args)",
                "args": {
                    "start_symbol_id": "655aefae-4cff-497f-91ea-1e1a5e4680fc",
                    "start_pin_number": "1",
                    "end_symbol_id": "2fd88b1c-8672-4fdd-aa87-2081ce63a903",
                    "end_pin_number": "2",
                    "symbols_data": "[...from get_symbol_positions()...]",
                    "routing_mode": "manhattan"
                }
            }
        }
    
    def smart_route_step_3(self, args: Dict[str, Any]):
        """
        Step 3: Execute smart routing and create wire segments.
        
        This performs intelligent routing analysis and generates the optimal
        path between the specified pins, then creates the wire segments.
        
        Args:
            args: Dictionary containing routing parameters
                - start_symbol_id: UUID of starting symbol
                - start_pin_number: Pin number on start symbol
                - end_symbol_id: UUID of ending symbol
                - end_pin_number: Pin number on end symbol
                - symbols_data: Complete symbol data from get_symbol_positions
                - routing_mode: Optional routing mode (default: 'manhattan')
        
        Returns:
            Routing results with analysis and wire creation commands
        """
        try:
            # Extract parameters
            start_symbol_id = args.get('start_symbol_id')
            start_pin_number = args.get('start_pin_number')
            end_symbol_id = args.get('end_symbol_id')
            end_pin_number = args.get('end_pin_number')
            symbols_data = args.get('symbols_data')
            routing_mode = args.get('routing_mode', 'manhattan')
            
            # Validate required parameters
            if not all([start_symbol_id, start_pin_number, end_symbol_id, 
                       end_pin_number, symbols_data]):
                return {
                    "error": "Missing required parameters",
                    "required": ["start_symbol_id", "start_pin_number", 
                                "end_symbol_id", "end_pin_number", "symbols_data"]
                }
            
            # Execute smart routing
            result = self.smart_wire_tool.smart_draw_wire_between_pins(
                start_symbol_id=start_symbol_id,
                start_pin_number=str(start_pin_number),
                end_symbol_id=end_symbol_id,
                end_pin_number=str(end_pin_number),
                symbols_data=symbols_data,
                routing_mode=routing_mode
            )
            
            if result.get('success'):
                # Create the actual wires in KiCad
                wire_creation_results = []
                for segment in result.get('wire_segments', []):
                    # Import here to avoid circular dependency
                    from kipy.proto.schematic import schematic_commands_pb2
                    from kipy.proto.common.types import base_types_pb2
                    
                    # Get the active schematic document
                    doc_spec = self.get_active_schematic_document()
                    if not doc_spec:
                        return {"error": "No schematic document available"}
                    
                    # Create DrawWire request for this segment
                    request = schematic_commands_pb2.DrawWire()
                    request.schematic.CopyFrom(doc_spec)
                    request.start_point.x_nm = segment['start_point']['x_nm']
                    request.start_point.y_nm = segment['start_point']['y_nm']
                    request.end_point.x_nm = segment['end_point']['x_nm']
                    request.end_point.y_nm = segment['end_point']['y_nm']
                    
                    # Send wire creation command
                    response = self.send_schematic_command("DrawWire", request)
                    
                    if response.wire_id.value:
                        wire_creation_results.append({
                            "wire_id": response.wire_id.value,
                            "segment": segment
                        })
                    else:
                        wire_creation_results.append({
                            "error": response.error or "Failed to create wire",
                            "segment": segment
                        })
                
                # Return comprehensive results
                return {
                    "workflow": "Smart Wire Routing - Step 3 of 3",
                    "status": "success",
                    "routing_analysis": result.get('routing_analysis'),
                    "pin_info": result.get('pin_info'),
                    "wires_created": len(wire_creation_results),
                    "wire_details": wire_creation_results,
                    "recommendations": result.get('routing_recommendations'),
                    "next_actions": [
                        "get_schematic_status() to verify wire creation",
                        "smart_route_step_1() to route another connection",
                        "analyze_routing_path() to review routing quality"
                    ]
                }
            else:
                return {
                    "workflow": "Smart Wire Routing - Step 3 of 3",
                    "status": "failed",
                    "error": result.get('error', 'Unknown routing error'),
                    "troubleshooting": result.get('troubleshooting', [])
                }
                
        except Exception as e:
            return {
                "workflow": "Smart Wire Routing - Step 3 of 3",
                "status": "error",
                "error": f"Smart routing failed: {str(e)}",
                "troubleshooting": [
                    "Verify symbol IDs are correct",
                    "Check pin numbers exist on symbols",
                    "Ensure symbols_data is from get_symbol_positions()"
                ]
            }
    
    def analyze_routing_path(self, start_pos: Dict[str, int], end_pos: Dict[str, int]):
        """
        Analyze potential routing path without creating wires.
        
        This tool evaluates the routing path quality and provides
        recommendations without modifying the schematic.
        
        Args:
            start_pos: Starting position with x_nm and y_nm
            end_pos: Ending position with x_nm and y_nm
            
        Returns:
            Analysis of the routing path with quality metrics
        """
        try:
            from ..smart_routing import Position, SmartRoutingEngine
            
            # Create position objects
            start = Position(start_pos['x_nm'], start_pos['y_nm'])
            end = Position(end_pos['x_nm'], end_pos['y_nm'])
            
            # Calculate distances and angles
            euclidean_distance = start.distance_to(end)
            manhattan_distance = start.manhattan_distance_to(end)
            
            # Determine routing quality
            if manhattan_distance == euclidean_distance:
                quality = "Perfect - Already aligned horizontally or vertically"
            elif manhattan_distance < euclidean_distance * 1.5:
                quality = "Good - Minor detour required"
            else:
                quality = "Complex - Significant routing challenge"
            
            return {
                "analysis": "Routing Path Analysis",
                "start_position": start_pos,
                "end_position": end_pos,
                "metrics": {
                    "euclidean_distance_nm": euclidean_distance,
                    "manhattan_distance_nm": manhattan_distance,
                    "euclidean_mm": euclidean_distance / 1_000_000,
                    "manhattan_mm": manhattan_distance / 1_000_000,
                    "efficiency_ratio": euclidean_distance / manhattan_distance if manhattan_distance > 0 else 1.0
                },
                "routing_quality": quality,
                "recommendations": [
                    "Use Manhattan routing for professional appearance",
                    "Consider component positions to minimize crossings",
                    "Align components on grid for cleaner routing"
                ]
            }
        except Exception as e:
            return {
                "error": f"Analysis failed: {str(e)}"
            }
    
    def preview_smart_route(self, args: Dict[str, Any]):
        """
        Preview smart routing path without creating wires.
        
        This allows testing routing algorithms and viewing the planned
        path before committing to wire creation.
        
        Args:
            args: Same parameters as smart_route_step_3
            
        Returns:
            Routing preview with path segments but no wire creation
        """
        try:
            # Extract parameters
            start_symbol_id = args.get('start_symbol_id')
            start_pin_number = args.get('start_pin_number')
            end_symbol_id = args.get('end_symbol_id')
            end_pin_number = args.get('end_pin_number')
            symbols_data = args.get('symbols_data')
            routing_mode = args.get('routing_mode', 'manhattan')
            
            # Execute smart routing without wire creation
            result = self.smart_wire_tool.smart_draw_wire_between_pins(
                start_symbol_id=start_symbol_id,
                start_pin_number=str(start_pin_number),
                end_symbol_id=end_symbol_id,
                end_pin_number=str(end_pin_number),
                symbols_data=symbols_data,
                routing_mode=routing_mode
            )
            
            if result.get('success'):
                return {
                    "preview": "Smart Routing Preview",
                    "status": "success",
                    "routing_analysis": result.get('routing_analysis'),
                    "pin_info": result.get('pin_info'),
                    "planned_segments": result.get('wire_segments'),
                    "recommendations": result.get('routing_recommendations'),
                    "note": "This is a preview only - no wires were created",
                    "to_create": "Use smart_route_step_3() with same parameters to create wires"
                }
            else:
                return {
                    "preview": "Smart Routing Preview",
                    "status": "failed",
                    "error": result.get('error', 'Preview generation failed')
                }
                
        except Exception as e:
            return {
                "preview": "Smart Routing Preview",
                "error": f"Preview failed: {str(e)}"
            }


class SchematicSmartRoutingTools:
    """Factory class for registering smart routing tools with MCP."""
    
    @staticmethod
    def register_tools(mcp: FastMCP):
        """Register all smart routing tools with the MCP server."""
        SchematicSmartRouter(mcp)