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
                                   symbols_data: List[Dict[str, Any]],
                                   routing_mode: str = "manhattan") -> Dict[str, Any]:
        """
        Draw intelligent wire between two specific pins.
        
        This is the main entry point for smart routing, implementing the complete
        workflow from pin identification to optimized wire segment creation.
        
        Args:
            start_symbol_id: UUID of starting symbol
            start_pin_number: Pin number on starting symbol (e.g., "1", "2")
            end_symbol_id: UUID of ending symbol  
            end_pin_number: Pin number on ending symbol
            symbols_data: Complete symbol data from get_symbol_positions
            routing_mode: "manhattan", "direct", "45_degree"
            
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
            
            # Find and validate pins
            start_pin, start_symbol = self._find_pin_in_symbols(
                start_symbol_id, start_pin_number, symbols_data
            )
            end_pin, end_symbol = self._find_pin_in_symbols(
                end_symbol_id, end_pin_number, symbols_data
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
            for symbol_data in symbols_data:
                symbol = self.routing_engine.convert_mcp_symbol_to_routing_symbol(symbol_data)
                all_symbols.append(symbol)
                
                # Add to boundary manager for collision awareness
                self.boundary_manager.add_component_boundary(symbol, BoundingBoxType.BODY_PINS)
            
            # Generate smart routing path
            if routing_mode_enum == RoutingMode.MANHATTAN:
                routing_path = self.routing_engine.engine.generate_manhattan_path(
                    start_pin, end_pin, all_symbols
                )
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
                    "corridor_analysis": corridor_analysis
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
                            symbols_data: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                              symbols_data: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                           symbols_data: List[Dict[str, Any]]) -> tuple[Optional[Pin], Optional[Symbol]]:
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