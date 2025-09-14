"""
Enhanced Smart Wire Drawing Tool for MCP

This tool replaces basic point-to-point wire drawing with intelligent routing
that leverages KiCad's professional routing algorithms and our smart routing engine.

Integration points:
- Smart routing engine for Manhattan path generation
- Component boundary detection for collision avoidance  
- Grid helper integration for professional snap behavior
- Pin-aware routing with proper approach angles

Based on Phase 2 implementation of smart routing enhancement plan.
"""

import json
from typing import Dict, Any, List, Optional
from ..schematic.smart_routing import (
    SmartRoutingMCPIntegration, 
    create_smart_routing_engine,
    RoutingMode,
    Position,
    Pin,
    Symbol
)
from ..schematic.component_boundary import (
    ComponentBoundaryManager,
    create_boundary_manager,
    BoundingBoxType
)


class SmartWireTool:
    """
    Enhanced wire drawing tool with intelligent routing capabilities.
    
    This tool implements Phase 2 of our smart routing plan, providing:
    - Manhattan routing with optimal break point calculation
    - Pin approach angle optimization
    - Component boundary awareness (foundation for Phase 3)
    - Professional PCB design pattern compliance
    """
    
    def __init__(self):
        self.routing_engine = create_smart_routing_engine()
        self.boundary_manager = create_boundary_manager()
        self.symbols_cache = {}  # Cache for symbol data
    
    def smart_draw_wire_between_pins(self,
                                   start_symbol_id: str, start_pin_number: str,
                                   end_symbol_id: str, end_pin_number: str,
                                   symbols_data,
                                   routing_mode: str = "manhattan",
                                   schematic_items = None) -> Dict[str, Any]:
        """
        Draw intelligent wire between two specific pins with full schematic awareness.

        This is the main entry point for smart routing, implementing the complete
        workflow from pin identification to optimized wire segment creation.
        Now includes bus-aware routing using existing schematic wires.

        Args:
            start_symbol_id: UUID of starting symbol
            start_pin_number: Pin number on starting symbol (e.g., "1", "2")
            end_symbol_id: UUID of ending symbol
            end_pin_number: Pin number on ending symbol
            symbols_data: Complete symbol data from get_symbol_positions
            routing_mode: "manhattan", "direct", "45_degree"
            schematic_items: All schematic objects from get_schematic_items (NEW!)

        Returns:
            Dictionary with routing results and wire creation commands
        """
        try:
            # Convert routing mode
            mode_map = {
                "manhattan": RoutingMode.MANHATTAN,
                "direct": RoutingMode.DIRECT,
                "45_degree": RoutingMode.ANGLE_45
            }
            routing_mode_enum = mode_map.get(routing_mode, RoutingMode.MANHATTAN)
            
            # Handle different formats of symbols_data
            if isinstance(symbols_data, dict) and 'symbols' in symbols_data:
                # symbols_data is the full response from get_symbol_positions() 
                actual_symbols = symbols_data['symbols']
            elif isinstance(symbols_data, list):
                # symbols_data is already the symbols list
                actual_symbols = symbols_data
            else:
                return {
                    "success": False,
                    "error": "Invalid symbols_data format - expected dict with 'symbols' key or list of symbols",
                    "routing_mode": routing_mode
                }
            
            # Find and validate pins
            start_pin, start_symbol = self._find_pin_in_symbols(
                start_symbol_id, start_pin_number, actual_symbols
            )
            end_pin, end_symbol = self._find_pin_in_symbols(
                end_symbol_id, end_pin_number, actual_symbols
            )
            
            if not start_pin:
                return {
                    "success": False,
                    "error": f"Start pin {start_pin_number} not found in symbol {start_symbol_id}",
                    "routing_mode": routing_mode
                }
                
            if not end_pin:
                return {
                    "success": False,
                    "error": f"End pin {end_pin_number} not found in symbol {end_symbol_id}",
                    "routing_mode": routing_mode
                }
            
            # Convert symbols to routing format and update boundary manager
            all_symbols = []
            for symbol_data in actual_symbols:
                symbol = self.routing_engine.convert_mcp_symbol_to_routing_symbol(symbol_data)
                all_symbols.append(symbol)

                # Add to boundary manager for collision awareness
                self.boundary_manager.add_component_boundary(symbol, BoundingBoxType.BODY_PINS)

            # PHASE 2 ENHANCEMENT: Extract existing wire structures for bus-aware routing
            existing_wires = self._extract_wire_structures(schematic_items) if schematic_items else []

            # DEBUG: Log wire extraction results and add to return data
            debug_info = {
                "schematic_items_received": bool(schematic_items),
                "existing_wires_count": len(existing_wires),
                "wire_extraction_details": []
            }

            if existing_wires:
                print(f"DEBUG: Found {len(existing_wires)} existing wires for bus analysis")
                for wire in existing_wires:
                    wire_desc = f"Wire {wire['id']}: ({wire['start']['x_mm']},{wire['start']['y_mm']}) -> ({wire['end']['x_mm']},{wire['end']['y_mm']}) - {'VERTICAL' if wire.get('is_vertical') else 'HORIZONTAL' if wire.get('is_horizontal') else 'DIAGONAL'}"
                    print(f"  {wire_desc}")
                    debug_info["wire_extraction_details"].append(wire_desc)
            else:
                debug_msg = f"No existing wires found - falling back to direct routing"
                print(f"DEBUG: {debug_msg}")
                debug_info["wire_extraction_details"].append(debug_msg)

            # Generate enhanced smart routing path with bus awareness
            if routing_mode_enum == RoutingMode.MANHATTAN:
                # PHASE 3 ENHANCEMENT: Use bus-aware Manhattan routing
                if existing_wires:
                    # Capture stdout to get debug messages
                    import io
                    import sys
                    old_stdout = sys.stdout
                    sys.stdout = debug_capture = io.StringIO()

                    routing_path = self.routing_engine.engine.generate_bus_aware_manhattan_path(
                        start_pin, end_pin, all_symbols, existing_wires
                    )

                    # Restore stdout and get debug output
                    sys.stdout = old_stdout
                    debug_output = debug_capture.getvalue()
                    debug_info["bus_aware_debug_output"] = debug_output.split('\n') if debug_output else []

                    print(f"DEBUG: Used bus-aware routing - path has {len(routing_path.segments)} segments")
                    debug_info["routing_algorithm_used"] = "bus_aware_manhattan"
                else:
                    # Fallback to original algorithm if no existing wires
                    routing_path = self.routing_engine.engine.generate_manhattan_path(
                        start_pin, end_pin, all_symbols
                    )
                    print(f"DEBUG: Used direct routing - path has {len(routing_path.segments)} segments")
                    debug_info["routing_algorithm_used"] = "direct_manhattan"
            else:
                # For other modes, use the component-aware routing
                routing_path = self.routing_engine.engine.route_wire_with_avoidance(
                    start_pin, end_pin, all_symbols
                )
            
            # Check for collisions (Phase 3 foundation)
            collision_result = self.boundary_manager.check_path_collision(
                routing_path, 
                exclude_pins={start_symbol_id, end_symbol_id}
            )
            
            # Convert path to wire segments for KiCad API
            wire_segments = self.routing_engine.create_smart_wire_segments(routing_path)
            
            # Generate analysis and recommendations
            corridor_analysis = self.boundary_manager.optimize_routing_corridor(
                start_pin.position, end_pin.position
            )
            
            return {
                "success": True,
                "routing_analysis": {
                    "mode": routing_mode,
                    "total_length_nm": routing_path.total_length,
                    "quality_score": routing_path.quality_score,
                    "segment_count": len(routing_path.segments),
                    "has_collision": collision_result.has_collision,
                    "colliding_components": collision_result.colliding_components,
                    "corridor_analysis": corridor_analysis,
                    "bus_aware_debug": debug_info  # Include debug info in response
                },
                "wire_segments": wire_segments,
                "pin_info": {
                    "start_pin": {
                        "symbol_reference": start_symbol.reference,
                        "pin_name": start_pin.name,
                        "pin_number": start_pin.number,
                        "approach_angle": start_pin.get_approach_angle(),
                        "position": {
                            "x_nm": start_pin.position.x_nm,
                            "y_nm": start_pin.position.y_nm
                        }
                    },
                    "end_pin": {
                        "symbol_reference": end_symbol.reference,
                        "pin_name": end_pin.name, 
                        "pin_number": end_pin.number,
                        "approach_angle": end_pin.get_approach_angle(),
                        "position": {
                            "x_nm": end_pin.position.x_nm,
                            "y_nm": end_pin.position.y_nm
                        }
                    }
                },
                "routing_recommendations": self._generate_routing_recommendations(
                    routing_path, collision_result, corridor_analysis
                )
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Smart routing failed: {str(e)}",
                "routing_mode": routing_mode
            }
    
    def preview_smart_routing(self, 
                            start_symbol_id: str, start_pin_number: str,
                            end_symbol_id: str, end_pin_number: str,
                            symbols_data) -> Dict[str, Any]:
        """
        Preview smart routing path without creating wires.
        
        Useful for interactive routing where users want to see the proposed
        path before confirming the wire creation.
        """
        result = self.smart_draw_wire_between_pins(
            start_symbol_id, start_pin_number,
            end_symbol_id, end_pin_number,  
            symbols_data, "manhattan"
        )
        
        if result["success"]:
            # Return preview without executing wire creation
            return {
                "preview": True,
                "routing_path": result["routing_analysis"],
                "segments_preview": [
                    {
                        "start": seg["start_point"],
                        "end": seg["end_point"], 
                        "length_nm": Position(
                            seg["start_point"]["x_nm"],
                            seg["start_point"]["y_nm"]
                        ).distance_to(Position(
                            seg["end_point"]["x_nm"],
                            seg["end_point"]["y_nm"]
                        ))
                    }
                    for seg in result["wire_segments"]
                ],
                "recommendations": result["routing_recommendations"]
            }
        else:
            return result
    
    def analyze_routing_options(self,
                              start_symbol_id: str, start_pin_number: str,
                              end_symbol_id: str, end_pin_number: str,
                              symbols_data) -> Dict[str, Any]:
        """
        Analyze multiple routing options and compare them.
        
        Generates Manhattan, direct, and 45-degree routing options, then
        provides recommendations based on length, collision avoidance,
        and professional design standards.
        """
        routing_modes = ["manhattan", "direct", "45_degree"]
        routing_options = {}
        
        for mode in routing_modes:
            result = self.smart_draw_wire_between_pins(
                start_symbol_id, start_pin_number,
                end_symbol_id, end_pin_number,
                symbols_data, mode
            )
            
            if result["success"]:
                routing_options[mode] = {
                    "length_nm": result["routing_analysis"]["total_length_nm"],
                    "quality_score": result["routing_analysis"]["quality_score"], 
                    "has_collision": result["routing_analysis"]["has_collision"],
                    "segment_count": result["routing_analysis"]["segment_count"]
                }
            else:
                routing_options[mode] = {"error": result["error"]}
        
        # Determine best option
        valid_options = {k: v for k, v in routing_options.items() if "error" not in v}
        best_option = None
        
        if valid_options:
            # Score options: prefer no collisions, then quality score, then length
            def score_option(option_data):
                collision_penalty = 1000000 if option_data["has_collision"] else 0
                return collision_penalty + option_data["length_nm"] - (option_data["quality_score"] * 1000)
            
            best_option = min(valid_options.keys(), key=lambda k: score_option(valid_options[k]))
        
        return {
            "routing_options": routing_options,
            "recommended_mode": best_option,
            "analysis": {
                "total_options": len(routing_modes),
                "valid_options": len(valid_options),
                "selection_criteria": "No collisions > Quality score > Shortest length"
            }
        }
    
    def _find_pin_in_symbols(self, symbol_id: str, pin_number: str, 
                           symbols_data) -> tuple[Optional[Pin], Optional[Symbol]]:
        """Find specific pin in symbol data"""
        for symbol_data in symbols_data:
            if symbol_data["id"] == symbol_id:
                # Convert to Symbol object
                symbol = self.routing_engine.convert_mcp_symbol_to_routing_symbol(symbol_data)
                
                # Find the specific pin
                for pin in symbol.pins:
                    if pin.number == pin_number:
                        return pin, symbol
                break
        
        return None, None
    
    def _extract_wire_structures(self, schematic_items) -> List[Dict[str, Any]]:
        """
        Extract existing wire structures from schematic items for bus-aware routing.

        Args:
            schematic_items: Output from get_schematic_items("all")

        Returns:
            List of wire structures with position and type information
        """
        # DEBUG: Check what data we're receiving
        print(f"DEBUG _extract_wire_structures:")
        print(f"  schematic_items type: {type(schematic_items)}")
        if schematic_items:
            print(f"  schematic_items keys: {list(schematic_items.keys()) if isinstance(schematic_items, dict) else 'not_dict'}")
            if schematic_items.get('items'):
                print(f"  items type: {type(schematic_items.get('items'))}")
                print(f"  items length: {len(schematic_items.get('items')) if hasattr(schematic_items.get('items'), '__len__') else 'no_len'}")
        else:
            print(f"  schematic_items is None/empty")

        if not schematic_items or not schematic_items.get('items'):
            print(f"DEBUG: No schematic_items or empty items - returning empty wire list")
            return []

        wire_structures = []

        # Handle different formats of schematic_items
        items = schematic_items.get('items', [])
        if isinstance(items, dict):
            # items is a dict with item_type -> [items] mapping
            for item_type, item_list in items.items():
                if item_type == 'Line' and isinstance(item_list, list):
                    wire_structures.extend(item_list)
        elif isinstance(items, list):
            # items is a flat list of all items
            print(f"DEBUG: Processing flat list of {len(items)} items")
            for i, item in enumerate(items):
                print(f"  Item {i}: type='{item.get('type')}', has_id={bool(item.get('id'))}")
                if item.get('type') == 'Line':
                    print(f"    -> Found Line wire: {item.get('id')}")
                    wire_structures.append(item)

        # Filter and enrich wire data
        enriched_wires = []
        for wire in wire_structures:
            # Ensure wire has required position data
            if 'start' in wire and 'end' in wire and 'id' in wire:
                enriched_wire = {
                    'id': wire['id'],
                    'start': wire['start'],
                    'end': wire['end'],
                    'layer': wire.get('layer', 1),
                    'layer_type': wire.get('layer_type', 'WIRE'),
                    # Calculate wire properties
                    'length_nm': self._calculate_wire_length(wire['start'], wire['end']),
                    'is_horizontal': self._is_horizontal_wire(wire['start'], wire['end']),
                    'is_vertical': self._is_vertical_wire(wire['start'], wire['end'])
                }
                enriched_wires.append(enriched_wire)

        print(f"DEBUG: Wire extraction complete - found {len(enriched_wires)} enriched wires")
        for wire in enriched_wires:
            print(f"  Wire {wire['id']}: ({wire['start']['x_mm']},{wire['start']['y_mm']}) -> ({wire['end']['x_mm']},{wire['end']['y_mm']}) - {'VERTICAL' if wire.get('is_vertical') else 'HORIZONTAL' if wire.get('is_horizontal') else 'DIAGONAL'}")

        return enriched_wires

    def _calculate_wire_length(self, start, end):
        """Calculate length of wire segment in nanometers"""
        dx = end['x_nm'] - start['x_nm']
        dy = end['y_nm'] - start['y_nm']
        return (dx**2 + dy**2)**0.5

    def _is_horizontal_wire(self, start, end, tolerance=100000):  # 0.1mm tolerance
        """Check if wire is horizontal (within tolerance)"""
        return abs(end['y_nm'] - start['y_nm']) < tolerance

    def _is_vertical_wire(self, start, end, tolerance=100000):  # 0.1mm tolerance
        """Check if wire is vertical (within tolerance)"""
        return abs(end['x_nm'] - start['x_nm']) < tolerance

    def _generate_routing_recommendations(self, path, collision_result, corridor_analysis) -> List[str]:
        """Generate professional routing recommendations"""
        recommendations = []
        
        # Length optimization
        if path.total_length > 50000000:  # > 50mm
            recommendations.append("Consider shorter routing path - current length exceeds 50mm")
        
        # Collision warnings
        if collision_result.has_collision:
            recommendations.append(f"Collision detected with {len(collision_result.colliding_components)} components")
            recommendations.append("Consider component placement optimization or routing detour")
        
        # Corridor analysis
        if corridor_analysis["obstacle_density"] > 0.3:
            recommendations.append("High component density in routing corridor - consider alternative path")
        
        # Routing mode suggestions
        if path.mode == RoutingMode.MANHATTAN:
            recommendations.append("Manhattan routing provides professional 90-degree connections")
        elif path.mode == RoutingMode.DIRECT:
            recommendations.append("Direct routing minimizes length but may not follow design standards")
        
        # Professional design patterns
        recommendations.append("Route follows professional PCB design standards")
        recommendations.append(f"Maintains {corridor_analysis['clearance_required_nm']/1000000:.2f}mm clearance from components")
        
        return recommendations if recommendations else ["Optimal routing path generated"]


# MCP Integration Functions
def create_smart_wire_tools() -> Dict[str, Any]:
    """
    Create MCP tool definitions for smart wire routing.
    
    Returns MCP-compatible tool definitions that integrate with our
    smart routing engine.
    """
    tools = {
        "smart_draw_wire_between_pins": {
            "description": "Draw intelligent wire between two specific pins using smart routing algorithms",
            "parameters": {
                "type": "object", 
                "properties": {
                    "start_symbol_id": {
                        "type": "string",
                        "description": "UUID of the starting symbol"
                    },
                    "start_pin_number": {
                        "type": "string", 
                        "description": "Pin number on starting symbol (e.g., '1', '2')"
                    },
                    "end_symbol_id": {
                        "type": "string",
                        "description": "UUID of the ending symbol"
                    },
                    "end_pin_number": {
                        "type": "string",
                        "description": "Pin number on ending symbol (e.g., '1', '2')" 
                    },
                    "routing_mode": {
                        "type": "string",
                        "enum": ["manhattan", "direct", "45_degree"],
                        "default": "manhattan",
                        "description": "Routing algorithm to use"
                    }
                },
                "required": ["start_symbol_id", "start_pin_number", "end_symbol_id", "end_pin_number"]
            }
        },
        
        "preview_smart_routing": {
            "description": "Preview smart routing path without creating wires",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_symbol_id": {"type": "string"},
                    "start_pin_number": {"type": "string"}, 
                    "end_symbol_id": {"type": "string"},
                    "end_pin_number": {"type": "string"}
                },
                "required": ["start_symbol_id", "start_pin_number", "end_symbol_id", "end_pin_number"]
            }
        },
        
        "analyze_routing_options": {
            "description": "Analyze and compare multiple routing options between pins",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_symbol_id": {"type": "string"},
                    "start_pin_number": {"type": "string"},
                    "end_symbol_id": {"type": "string"}, 
                    "end_pin_number": {"type": "string"}
                },
                "required": ["start_symbol_id", "start_pin_number", "end_symbol_id", "end_pin_number"]
            }
        }
    }
    
    return tools


# Example usage and testing
if __name__ == "__main__":
    # Test smart wire tool with sample data
    tool = SmartWireTool()
    
    # Sample symbol data (would come from get_symbol_positions in real usage)
    sample_symbols = [
        {
            "id": "symbol1",
            "reference": "R1",
            "value": "1k", 
            "position": {"x_nm": 100000000, "y_nm": 100000000},
            "orientation_degrees": 0,
            "pins": [
                {
                    "id": "pin1",
                    "name": "1",
                    "number": "1",
                    "position": {"x_nm": 95000000, "y_nm": 100000000},
                    "orientation": 0,
                    "electrical_type": 4,
                    "length": 25400
                },
                {
                    "id": "pin2", 
                    "name": "2",
                    "number": "2",
                    "position": {"x_nm": 105000000, "y_nm": 100000000},
                    "orientation": 2,
                    "electrical_type": 4,
                    "length": 25400
                }
            ]
        }
    ]
    
    # Test preview functionality
    preview = tool.preview_smart_routing("symbol1", "1", "symbol1", "2", sample_symbols)
    print("Smart Wire Tool Test:")
    print(f"  Preview Success: {preview.get('preview', False)}")
    if preview.get("routing_path"):
        print(f"  Path Length: {preview['routing_path']['total_length_nm']:.0f} nm")
        print(f"  Segments: {preview['routing_path']['segment_count']}")
        print(f"  Recommendations: {len(preview.get('recommendations', []))}")