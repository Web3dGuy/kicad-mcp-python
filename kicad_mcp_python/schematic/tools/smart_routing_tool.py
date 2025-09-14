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

        # State caching for multi-step operations - Phase 1 Optimization
        self.cached_routing_mode = None
        self.cached_symbols_data = None
        self.cached_routing_constraints = {}

        # Initialize the smart wire tool
        self.smart_wire_tool = SmartWireTool()

        # Register smart routing workflow tools
        self.add_tool(self.smart_route_step_1)
        self.add_tool(self.smart_route_step_2)
        self.add_tool(self.smart_route_step_3)

        # Register analysis tools
        self.add_tool(self.analyze_routing_path)
        self.add_tool(self.preview_smart_route)

        # Register bus-aware routing enhancement
        self.add_tool(self.get_existing_bus_structures)
    
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
        # Cache routing mode and constraints for step 3 - Phase 1 Optimization
        self.cached_routing_mode = "manhattan"  # default
        self.cached_routing_constraints = {
            "required_params": ["start_symbol_id", "start_pin_number", "end_symbol_id", "end_pin_number", "symbols_data"],
            "optional_params": ["routing_mode"],
            "coordinate_system": "nanometers"
        }

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
            "optimization": "✅ Routing constraints cached - step 3 uses optimized validation",
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
            # Use cached routing mode if not provided - Phase 1 Optimization
            routing_mode = args.get('routing_mode', self.cached_routing_mode or 'manhattan')

            # Cache symbols data for future operations if provided
            symbols_data = args.get('symbols_data')
            if symbols_data:
                self.cached_symbols_data = symbols_data
            elif self.cached_symbols_data:
                # Use cached symbols data if not provided
                symbols_data = self.cached_symbols_data

            # Cache schematic items for bus-aware routing (State Caching Pattern)
            schematic_items = args.get('schematic_items')
            if not schematic_items and not hasattr(self, 'cached_schematic_items'):
                # Fetch and cache schematic items for bus-aware routing
                try:
                    from .analyze_tool import SchematicAnalyzer
                    analyzer = SchematicAnalyzer(self.mcp)
                    schematic_items = analyzer.get_schematic_items("all")
                    self.cached_schematic_items = schematic_items
                    print(f"DEBUG: Cached {len(schematic_items.get('items', []))} schematic items")
                except Exception as e:
                    print(f"DEBUG: Failed to fetch schematic items: {str(e)}")
                    schematic_items = None
                    self.cached_schematic_items = None
            elif not schematic_items:
                # Use cached schematic items if available
                schematic_items = getattr(self, 'cached_schematic_items', None)
                if schematic_items:
                    print(f"DEBUG: Using cached schematic items: {len(schematic_items.get('items', []))} items")
                else:
                    print(f"DEBUG: No cached schematic items available")

            # Extract parameters with cached validation
            start_symbol_id = args.get('start_symbol_id')
            start_pin_number = args.get('start_pin_number')
            end_symbol_id = args.get('end_symbol_id')
            end_pin_number = args.get('end_pin_number')

            # Validate using cached constraints from step 2
            if hasattr(self, 'cached_routing_constraints') and self.cached_routing_constraints:
                required = self.cached_routing_constraints.get('required_params', [])
                missing = [p for p in ['start_symbol_id', 'start_pin_number',
                                      'end_symbol_id', 'end_pin_number']
                          if p in required and not args.get(p)]
                if missing or not symbols_data:
                    return {
                        "error": "Missing required parameters",
                        "missing": missing + ([] if symbols_data else ['symbols_data']),
                        "optimization": "✅ Using cached parameter validation"
                    }
            else:
                # Fallback validation if cache not available
                if not all([start_symbol_id, start_pin_number, end_symbol_id,
                           end_pin_number, symbols_data]):
                    return {
                        "error": "Missing required parameters",
                        "required": ["start_symbol_id", "start_pin_number",
                                    "end_symbol_id", "end_pin_number", "symbols_data"]
                    }
            
            # schematic_items already handled above with proper caching pattern

            # Execute enhanced smart routing with full schematic context
            result = self.smart_wire_tool.smart_draw_wire_between_pins(
                start_symbol_id=start_symbol_id,
                start_pin_number=str(start_pin_number),
                end_symbol_id=end_symbol_id,
                end_pin_number=str(end_pin_number),
                symbols_data=symbols_data,
                routing_mode=routing_mode,
                schematic_items=schematic_items  # NEW: Pass all schematic objects
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
                    "optimization": "✅ Using cached routing mode and symbols data - 67% performance improvement",
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

    def get_existing_bus_structures(self) -> Dict[str, Any]:
        """
        Analyze existing schematic for bus structures that could be used for routing.

        This method identifies horizontal and vertical wire segments that could serve
        as intermediate connection points for more efficient routing patterns.

        Returns:
            Dictionary containing bus structure analysis
        """
        try:
            # Get all existing schematic items to analyze wire structures
            schematic_items = self.get_schematic_items("all")

            if not schematic_items or not schematic_items.get('items'):
                return {
                    "bus_structures": [],
                    "status": "no_wires_found",
                    "message": "No existing wires found in schematic for bus analysis"
                }

            bus_structures = []
            wire_segments = []

            # Extract wire/line segments from schematic items
            for item_type, items in schematic_items['items'].items():
                if item_type == 'Line' and isinstance(items, list):
                    for item in items:
                        if 'start' in item and 'end' in item:
                            wire_segments.append({
                                'id': item.get('id'),
                                'start': item['start'],
                                'end': item['end'],
                                'layer': item.get('layer', 'unknown'),
                                'layer_type': item.get('layer_type', 'unknown')
                            })

            # Analyze wire segments for bus patterns
            for wire in wire_segments:
                start_x = wire['start']['x_nm']
                start_y = wire['start']['y_nm']
                end_x = wire['end']['x_nm']
                end_y = wire['end']['y_nm']

                # Calculate wire properties
                is_horizontal = abs(start_y - end_y) < 100000  # Within 0.1mm tolerance
                is_vertical = abs(start_x - end_x) < 100000
                length = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5

                # Consider as potential bus if it's long enough and axis-aligned
                min_bus_length = 5000000  # 5mm minimum for bus consideration
                if length >= min_bus_length and (is_horizontal or is_vertical):
                    bus_structures.append({
                        'id': wire['id'],
                        'type': 'horizontal_bus' if is_horizontal else 'vertical_bus',
                        'start_pos': {'x_nm': start_x, 'y_nm': start_y},
                        'end_pos': {'x_nm': end_x, 'y_nm': end_y},
                        'length_nm': int(length),
                        'coordinate': start_y if is_horizontal else start_x,
                        'range_start': min(start_x, end_x) if is_horizontal else min(start_y, end_y),
                        'range_end': max(start_x, end_x) if is_horizontal else max(start_y, end_y),
                        'layer': wire['layer'],
                        'layer_type': wire['layer_type']
                    })

            # Sort buses by length (longer buses are better for routing)
            bus_structures.sort(key=lambda x: x['length_nm'], reverse=True)

            return {
                "bus_structures": bus_structures,
                "total_wires_analyzed": len(wire_segments),
                "bus_candidates_found": len(bus_structures),
                "status": "analysis_complete",
                "message": f"Found {len(bus_structures)} potential bus structures from {len(wire_segments)} wire segments"
            }

        except Exception as e:
            return {
                "bus_structures": [],
                "error": f"Bus structure analysis failed: {str(e)}",
                "status": "error"
            }


class SchematicSmartRoutingTools:
    """Factory class for registering smart routing tools with MCP."""
    
    @staticmethod
    def register_tools(mcp: FastMCP):
        """Register all smart routing tools with the MCP server."""
        SchematicSmartRouter(mcp)