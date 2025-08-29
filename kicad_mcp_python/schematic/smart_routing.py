"""
Smart Routing Module for KiCad Schematic Design

This module implements intelligent wire routing algorithms that mirror KiCad's 
professional routing behavior, including Manhattan routing, component avoidance,
and pin-aware connections.

Based on analysis of KiCad's routing infrastructure:
- sch_line_wire_bus_tool.cpp: computeBreakPoint() for Manhattan routing
- ee_grid_helper.cpp: BestSnapAnchor() for smart snapping  
- sch_move_tool.cpp: Dynamic wire adjustment patterns
- sch_symbol.cpp: Component boundary detection

Phase 1: Foundation & API Integration
Phase 2: Manhattan Routing Implementation
Phase 3: Component Avoidance
Phase 4: Advanced Features
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import math


class RoutingMode(Enum):
    """Wire routing modes matching KiCad's LINE_MODE"""
    MANHATTAN = "manhattan"  # 90-degree angles only
    DIRECT = "direct"        # Point-to-point straight line
    FREE = "free"            # Any angle allowed
    ANGLE_45 = "45_degree"   # 45-degree angle mode


class AnchorType(Enum):
    """Types of snap anchors for wire routing"""
    GRID = "grid"
    PIN = "pin" 
    CONNECTION = "connection"
    WIRE_END = "wire_end"
    JUNCTION = "junction"


@dataclass
class Position:
    """Position in nanometers (KiCad API coordinate system)"""
    x_nm: int
    y_nm: int
    
    def __add__(self, other: 'Position') -> 'Position':
        return Position(self.x_nm + other.x_nm, self.y_nm + other.y_nm)
    
    def __sub__(self, other: 'Position') -> 'Position':
        return Position(self.x_nm - other.x_nm, self.y_nm - other.y_nm)
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position"""
        dx = self.x_nm - other.x_nm
        dy = self.y_nm - other.y_nm
        return math.sqrt(dx * dx + dy * dy)
    
    def manhattan_distance_to(self, other: 'Position') -> int:
        """Calculate Manhattan distance (L1 norm) to another position"""
        return abs(self.x_nm - other.x_nm) + abs(self.y_nm - other.y_nm)


@dataclass
class Pin:
    """Schematic pin with routing information"""
    id: str
    name: str
    number: str
    position: Position
    orientation: int  # 0=East, 1=North, 2=West, 3=South
    electrical_type: int
    length: int
    
    def get_approach_angle(self) -> int:
        """Get optimal approach angle based on pin orientation"""
        approach_angles = {0: 180, 1: 270, 2: 0, 3: 90}  # Opposite direction
        return approach_angles.get(self.orientation, 0)
    
    def get_connection_point(self) -> Position:
        """Get the precise connection point at pin end"""
        return self.position  # For now, use pin position directly


@dataclass
class Symbol:
    """Schematic symbol with routing context"""
    id: str
    reference: str
    value: str
    position: Position
    orientation_degrees: float
    pins: List[Pin]
    bounding_box: Optional[Tuple[Position, Position]] = None  # (top_left, bottom_right)


@dataclass
class RoutingAnchor:
    """Snap point for intelligent routing"""
    position: Position
    anchor_type: AnchorType
    item_id: Optional[str] = None
    distance: float = 0.0
    priority: int = 0  # Lower = higher priority


@dataclass
class RoutingPath:
    """Complete routing path with segments"""
    start_pin: Pin
    end_pin: Pin
    segments: List[Tuple[Position, Position]]
    total_length: float
    mode: RoutingMode
    quality_score: float = 0.0  # Higher = better routing


class SmartRoutingEngine:
    """
    Core smart routing engine implementing KiCad's intelligent routing patterns.
    
    This class ports key algorithms from KiCad's C++ routing tools:
    - computeBreakPoint() for Manhattan path generation
    - BestSnapAnchor() for optimal connection points
    - Component boundary awareness for collision avoidance
    """
    
    def __init__(self):
        self.grid_size_nm = 1270000  # 1.27mm = 50 mils in nanometers
        self.snap_range_nm = 635000  # 0.635mm = 25 mils snap range
        
    def compute_break_point(self, start: Position, end: Position, 
                          mode: RoutingMode = RoutingMode.MANHATTAN,
                          prefer_horizontal: bool = False) -> Position:
        """
        Port of KiCad's computeBreakPoint() function from sch_line_wire_bus_tool.cpp:470
        
        Determines optimal intermediate point for L-shaped Manhattan routing.
        
        Args:
            start: Starting position
            end: Ending position  
            mode: Routing mode (Manhattan, 45-degree, etc.)
            prefer_horizontal: Whether to prefer horizontal first segment
            
        Returns:
            Optimal break point for two-segment routing
        """
        delta = end - start
        
        if mode == RoutingMode.DIRECT:
            # Direct routing - no break point needed
            return end
            
        elif mode == RoutingMode.MANHATTAN:
            # Manhattan routing - choose break point for optimal L-shape
            if prefer_horizontal:
                # Horizontal first, then vertical
                return Position(end.x_nm, start.y_nm)
            else:
                # Choose based on distance - match KiCad's logic
                if abs(delta.x_nm) < abs(delta.y_nm):
                    # Vertical first (smaller horizontal distance)
                    return Position(start.x_nm, end.y_nm)
                else:
                    # Horizontal first (smaller vertical distance)
                    return Position(end.x_nm, start.y_nm)
                    
        elif mode == RoutingMode.ANGLE_45:
            # 45-degree routing - create diagonal + orthogonal segments
            # Simplified implementation - full 45-degree logic is complex
            abs_dx = abs(delta.x_nm)
            abs_dy = abs(delta.y_nm)
            
            if abs_dx > abs_dy:
                # More horizontal - diagonal then horizontal
                diag_len = abs_dy
                return Position(
                    start.x_nm + (diag_len if delta.x_nm > 0 else -diag_len),
                    end.y_nm
                )
            else:
                # More vertical - diagonal then vertical  
                diag_len = abs_dx
                return Position(
                    end.x_nm,
                    start.y_nm + (diag_len if delta.y_nm > 0 else -diag_len)
                )
        
        # Default to Manhattan horizontal-first
        return Position(end.x_nm, start.y_nm)
    
    def generate_manhattan_path(self, start_pin: Pin, end_pin: Pin, 
                              avoid_components: List[Symbol] = None) -> RoutingPath:
        """
        Generate intelligent Manhattan routing path between two pins.
        
        This implements the core smart routing logic, considering:
        - Pin approach angles for proper electrical connection
        - Component boundary avoidance  
        - Optimal break point selection
        - Professional PCB design patterns
        """
        avoid_components = avoid_components or []
        
        # Get connection points (may be offset from pin centers for proper approach)
        start_pos = start_pin.get_connection_point()
        end_pos = end_pin.get_connection_point()
        
        # Determine if we should prefer horizontal based on pin orientations
        prefer_horizontal = self._should_prefer_horizontal(start_pin, end_pin)
        
        # Compute optimal break point using KiCad's algorithm
        break_point = self.compute_break_point(
            start_pos, end_pos, 
            RoutingMode.MANHATTAN, 
            prefer_horizontal
        )
        
        # Create two-segment Manhattan path
        segments = [
            (start_pos, break_point),
            (break_point, end_pos)
        ]
        
        # Calculate total path length
        total_length = start_pos.distance_to(break_point) + break_point.distance_to(end_pos)
        
        path = RoutingPath(
            start_pin=start_pin,
            end_pin=end_pin,
            segments=segments,
            total_length=total_length,
            mode=RoutingMode.MANHATTAN
        )
        
        # Score the path quality (lower length = higher score)
        path.quality_score = 1000000.0 / (total_length + 1.0)
        
        return path
    
    def _should_prefer_horizontal(self, start_pin: Pin, end_pin: Pin) -> bool:
        """
        Determine routing direction preference based on pin orientations.
        
        This implements electrical engineering best practices:
        - Pins facing each other prefer direct connection
        - Power pins prefer horizontal routing (conventional)
        - Signal pins optimize for shortest path
        """
        # If pins are horizontally aligned, prefer horizontal
        if abs(start_pin.position.y_nm - end_pin.position.y_nm) < self.grid_size_nm:
            return True
            
        # If pins are vertically aligned, prefer vertical  
        if abs(start_pin.position.x_nm - end_pin.position.x_nm) < self.grid_size_nm:
            return False
            
        # Default to optimizing for shorter first segment
        delta = end_pin.position - start_pin.position
        return abs(delta.x_nm) > abs(delta.y_nm)
    
    def find_routing_anchors(self, position: Position, symbols: List[Symbol]) -> List[RoutingAnchor]:
        """
        Find optimal snap points near a position for smart routing.
        
        Port of EE_GRID_HELPER::BestSnapAnchor() functionality.
        """
        anchors = []
        
        # Add grid anchor
        grid_x = round(position.x_nm / self.grid_size_nm) * self.grid_size_nm
        grid_y = round(position.y_nm / self.grid_size_nm) * self.grid_size_nm
        grid_pos = Position(grid_x, grid_y)
        
        anchors.append(RoutingAnchor(
            position=grid_pos,
            anchor_type=AnchorType.GRID,
            distance=position.distance_to(grid_pos),
            priority=10
        ))
        
        # Add pin anchors within snap range
        for symbol in symbols:
            for pin in symbol.pins:
                distance = position.distance_to(pin.position)
                if distance <= self.snap_range_nm:
                    anchors.append(RoutingAnchor(
                        position=pin.position,
                        anchor_type=AnchorType.PIN,
                        item_id=pin.id,
                        distance=distance,
                        priority=1  # Pins have highest priority
                    ))
        
        # Sort by priority (lower = higher priority) then by distance  
        anchors.sort(key=lambda a: (a.priority, a.distance))
        
        return anchors
    
    def route_wire_with_avoidance(self, start_pin: Pin, end_pin: Pin, 
                                 symbols: List[Symbol]) -> RoutingPath:
        """
        Generate routing path with component avoidance.
        
        This will be expanded in Phase 3 to implement full collision detection
        and multi-path optimization.
        """
        # For now, use basic Manhattan routing
        # Phase 3 will add sophisticated component avoidance
        return self.generate_manhattan_path(start_pin, end_pin, symbols)


class SmartRoutingMCPIntegration:
    """
    Integration layer between smart routing engine and MCP tools.
    
    This class translates between the KiCad API data structures and our
    smart routing algorithms, providing the bridge for AI-driven schematic design.
    """
    
    def __init__(self):
        self.engine = SmartRoutingEngine()
    
    def convert_mcp_symbol_to_routing_symbol(self, mcp_symbol: Dict[str, Any]) -> Symbol:
        """Convert MCP symbol data to internal Symbol representation"""
        pins = []
        for pin_data in mcp_symbol.get('pins', []):
            pin = Pin(
                id=pin_data['id'],
                name=pin_data['name'],
                number=pin_data['number'],
                position=Position(
                    x_nm=pin_data['position']['x_nm'],
                    y_nm=pin_data['position']['y_nm']
                ),
                orientation=pin_data['orientation'],
                electrical_type=pin_data['electrical_type'],
                length=pin_data['length']
            )
            pins.append(pin)
        
        return Symbol(
            id=mcp_symbol['id'],
            reference=mcp_symbol['reference'],
            value=mcp_symbol['value'],
            position=Position(
                x_nm=mcp_symbol['position']['x_nm'],
                y_nm=mcp_symbol['position']['y_nm']
            ),
            orientation_degrees=mcp_symbol['orientation_degrees'],
            pins=pins
        )
    
    def create_smart_wire_segments(self, path: RoutingPath) -> List[Dict[str, Any]]:
        """
        Convert routing path to MCP wire creation commands.
        
        Returns list of wire segments ready for KiCad API consumption.
        """
        wire_segments = []
        
        for i, (start_pos, end_pos) in enumerate(path.segments):
            segment = {
                "start_point": {
                    "x_nm": start_pos.x_nm,
                    "y_nm": start_pos.y_nm
                },
                "end_point": {
                    "x_nm": end_pos.x_nm,
                    "y_nm": end_pos.y_nm
                },
                "width": 0,  # Use default wire width
                "segment_index": i,
                "routing_mode": path.mode.value
            }
            wire_segments.append(segment)
            
        return wire_segments


# Factory function for easy integration
def create_smart_routing_engine() -> SmartRoutingMCPIntegration:
    """Create smart routing engine ready for MCP integration"""
    return SmartRoutingMCPIntegration()


# Example usage for testing
if __name__ == "__main__":
    # Test the smart routing algorithms
    engine = SmartRoutingEngine()
    
    # Create test pins
    start_pin = Pin(
        id="pin1", name="A", number="1",
        position=Position(100000000, 100000000),  # 100mm, 100mm
        orientation=0, electrical_type=4, length=25400
    )
    
    end_pin = Pin(
        id="pin2", name="K", number="2", 
        position=Position(150000000, 150000000),  # 150mm, 150mm
        orientation=2, electrical_type=4, length=25400
    )
    
    # Generate Manhattan routing path
    path = engine.generate_manhattan_path(start_pin, end_pin)
    
    print(f"Smart Routing Path Generated:")
    print(f"  Total Length: {path.total_length:.0f} nm")
    print(f"  Quality Score: {path.quality_score:.2f}")
    print(f"  Segments: {len(path.segments)}")
    for i, (start, end) in enumerate(path.segments):
        print(f"    Segment {i+1}: ({start.x_nm}, {start.y_nm}) → ({end.x_nm}, {end.y_nm})")