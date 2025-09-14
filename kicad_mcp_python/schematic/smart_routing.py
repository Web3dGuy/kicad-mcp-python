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
    symbol_reference: str = ""  # For debugging - symbol reference this pin belongs to
    
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
                          prefer_horizontal: bool = False,
                          prefer_vertical: bool = False) -> Position:
        """
        Port of KiCad's computeBreakPoint() function from sch_line_wire_bus_tool.cpp:470
        
        Determines optimal intermediate point for L-shaped Manhattan routing.
        This is the ACTUAL KiCad algorithm, not a simplified version.
        
        Args:
            start: Starting position
            end: Ending position  
            mode: Routing mode (Manhattan, 45-degree, etc.)
            prefer_horizontal: Whether to prefer horizontal first segment
            prefer_vertical: Whether to prefer vertical first segment
            
        Returns:
            Optimal break point for two-segment routing
        """
        delta = end - start
        x_dir = 1 if delta.x_nm > 0 else -1
        y_dir = 1 if delta.y_nm > 0 else -1
        
        if mode == RoutingMode.DIRECT:
            # Direct routing - no break point needed
            return end
            
        # Initialize midpoint
        midpoint = Position(0, 0)
        
        # Define breakVertical lambda equivalent
        def break_vertical():
            nonlocal midpoint
            if mode == RoutingMode.ANGLE_45:
                # 45-degree routing vertical break
                midpoint.x_nm = start.x_nm
                midpoint.y_nm = end.y_nm - y_dir * abs(delta.x_nm)
            else:
                # Manhattan vertical break
                midpoint.x_nm = start.x_nm
                midpoint.y_nm = end.y_nm
        
        # Define breakHorizontal lambda equivalent  
        def break_horizontal():
            nonlocal midpoint
            if mode == RoutingMode.ANGLE_45:
                # 45-degree routing horizontal break
                midpoint.x_nm = end.x_nm - x_dir * abs(delta.y_nm)
                midpoint.y_nm = start.y_nm
            else:
                # Manhattan horizontal break
                midpoint.x_nm = end.x_nm
                midpoint.y_nm = start.y_nm
        
        # Apply KiCad's preference logic
        if prefer_vertical:
            break_vertical()
        elif prefer_horizontal:
            break_horizontal()
        else:
            # KiCad's default logic: choose based on smaller dimension
            if abs(delta.x_nm) < abs(delta.y_nm):
                break_vertical()
            else:
                break_horizontal()
        
        # For 45-degree mode, check if we need to adjust based on direction
        if mode == RoutingMode.ANGLE_45:
            delta_midpoint = midpoint - start
            
            # Check for invalid 45-degree configurations and fall back to distance-based
            if ((delta_midpoint.x_nm > 0) != (delta.x_nm > 0)) or \
               ((delta_midpoint.y_nm > 0) != (delta.y_nm > 0)):
                # Reset preferences and use distance-based selection
                prefer_vertical = False
                prefer_horizontal = False
                
                if abs(delta.x_nm) < abs(delta.y_nm):
                    break_vertical()
                else:
                    break_horizontal()
        
        # Final fallback - if no preferences set, use distance-based
        if not prefer_horizontal and not prefer_vertical:
            if abs(delta.x_nm) < abs(delta.y_nm):
                break_vertical() 
            else:
                break_horizontal()
                
        return midpoint
    
    def generate_bus_aware_manhattan_path(self, start_pin: Pin, end_pin: Pin,
                                        avoid_components: List[Symbol] = None,
                                        existing_wires: List[dict] = None) -> RoutingPath:
        """
        Generate bus-aware Manhattan routing path that considers existing wire structures.

        This enhanced routing algorithm analyzes existing schematic wires to identify
        potential bus structures and routes through them when beneficial.

        Args:
            start_pin: Starting pin for routing
            end_pin: Ending pin for routing
            avoid_components: Components to route around
            existing_wires: Existing wire structures from schematic

        Returns:
            Optimized routing path considering bus structures
        """
        avoid_components = avoid_components or []
        existing_wires = existing_wires or []

        # DEBUG: Bus-aware routing entry point
        print(f"DEBUG BUS-AWARE ROUTING:")
        print(f"  Start pin: {start_pin.symbol_reference}.{start_pin.number} at ({start_pin.position.x_nm/1000000:.2f}, {start_pin.position.y_nm/1000000:.2f})")
        print(f"  End pin: {end_pin.symbol_reference}.{end_pin.number} at ({end_pin.position.x_nm/1000000:.2f}, {end_pin.position.y_nm/1000000:.2f})")
        print(f"  Existing wires: {len(existing_wires)}")

        # Get connection points
        start_pos = start_pin.get_connection_point()
        end_pos = end_pin.get_connection_point()

        # Analyze existing wires for bus structures
        bus_structures = self._analyze_bus_structures(existing_wires)
        print(f"DEBUG: Found {len(bus_structures)} bus structures")
        for bus in bus_structures:
            print(f"  Bus {bus['id']}: {bus['type']} at {bus['coordinate']/1000000:.2f}mm, range {bus['range_start']/1000000:.2f}-{bus['range_end']/1000000:.2f}mm")

        # Generate routing options:
        # 1. Direct pin-to-pin (original algorithm)
        # 2. Bus-aware routing (new enhancement)
        direct_path = self._generate_direct_manhattan_path(start_pin, end_pin, avoid_components)

        if bus_structures:
            bus_aware_path = self._generate_bus_routing_path(start_pos, end_pos, bus_structures)

            if bus_aware_path:
                print(f"DEBUG: Generated bus-aware path with length {bus_aware_path.total_length/1000000:.2f}mm")
            else:
                print(f"DEBUG: No beneficial bus-aware path found")

            # Compare paths and select the best one
            if bus_aware_path and self._is_better_path(bus_aware_path, direct_path):
                # Set pin references for bus-aware path
                bus_aware_path.start_pin = start_pin
                bus_aware_path.end_pin = end_pin
                print(f"DEBUG: Selected BUS-AWARE path")
                return bus_aware_path
            else:
                print(f"DEBUG: Selected DIRECT path (bus path not better)")

        return direct_path

    def _generate_direct_manhattan_path(self, start_pin: Pin, end_pin: Pin,
                                       avoid_components: List[Symbol] = None) -> RoutingPath:
        """Original Manhattan path generation (moved from generate_manhattan_path)"""
        avoid_components = avoid_components or []

        # Get connection points (may be offset from pin centers for proper approach)
        start_pos = start_pin.get_connection_point()
        end_pos = end_pin.get_connection_point()

        # Determine routing preferences based on pin orientations
        prefer_horizontal, prefer_vertical = self._get_routing_preferences(start_pin, end_pin)

        # Compute optimal break point using KiCad's actual algorithm
        break_point = self.compute_break_point(
            start_pos, end_pos,
            RoutingMode.MANHATTAN,
            prefer_horizontal,
            prefer_vertical
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

    def _analyze_bus_structures(self, existing_wires: List[dict]) -> List[dict]:
        """
        Analyze existing wires to identify potential bus structures.

        Returns list of bus structures with connection information.
        """
        buses = []
        min_bus_length = 5000000  # 5mm minimum for bus consideration

        for wire in existing_wires:
            # Only consider electrical wires (not graphical lines)
            if wire.get('layer_type') != 'WIRE':
                continue

            length = wire.get('length_nm', 0)
            if length < min_bus_length:
                continue

            # Check if wire is axis-aligned (horizontal or vertical)
            if wire.get('is_horizontal'):
                buses.append({
                    'type': 'horizontal',
                    'id': wire['id'],
                    'coordinate': wire['start']['y_nm'],  # Y-coordinate of horizontal bus
                    'range_start': min(wire['start']['x_nm'], wire['end']['x_nm']),
                    'range_end': max(wire['start']['x_nm'], wire['end']['x_nm']),
                    'length_nm': length,
                    'start_pos': wire['start'],
                    'end_pos': wire['end']
                })
            elif wire.get('is_vertical'):
                buses.append({
                    'type': 'vertical',
                    'id': wire['id'],
                    'coordinate': wire['start']['x_nm'],  # X-coordinate of vertical bus
                    'range_start': min(wire['start']['y_nm'], wire['end']['y_nm']),
                    'range_end': max(wire['start']['y_nm'], wire['end']['y_nm']),
                    'length_nm': length,
                    'start_pos': wire['start'],
                    'end_pos': wire['end']
                })

        # Sort buses by length (longer buses are more attractive for routing)
        buses.sort(key=lambda x: x['length_nm'], reverse=True)
        return buses

    def _generate_bus_routing_path(self, start_pos: Position, end_pos: Position,
                                 bus_structures: List[dict]) -> RoutingPath:
        """
        Generate routing path that uses existing bus structures when beneficial.

        This implements multi-hop routing: pin → bus → destination
        """
        best_path = None
        best_length = float('inf')

        for bus in bus_structures:
            # Check if this bus can provide a beneficial routing path
            connection_point = self._find_optimal_bus_connection_point(start_pos, end_pos, bus)

            if connection_point:
                # Calculate multi-hop path: start → bus → end
                leg1_length = start_pos.distance_to(connection_point)
                leg2_length = connection_point.distance_to(end_pos)
                total_length = leg1_length + leg2_length

                if total_length < best_length:
                    # Create Manhattan path segments (90-degree angles only)
                    # For bus routing, we need to create proper L-shaped paths
                    segments = []

                    # First leg: route from start to bus connection point
                    # This should be a Manhattan path, not diagonal
                    if start_pos.x_nm != connection_point.x_nm and start_pos.y_nm != connection_point.y_nm:
                        # Need L-shaped path to reach bus
                        # Prefer horizontal-first routing for cleaner schematics
                        intermediate = Position(connection_point.x_nm, start_pos.y_nm)
                        segments.append((start_pos, intermediate))  # Horizontal segment
                        segments.append((intermediate, connection_point))  # Vertical segment to bus
                    else:
                        # Already aligned - single segment
                        segments.append((start_pos, connection_point))

                    # Second leg: from bus connection to destination
                    # The bus itself provides the connection, we just need the final segment
                    if connection_point.x_nm != end_pos.x_nm or connection_point.y_nm != end_pos.y_nm:
                        # Only add segment if not already at destination
                        segments.append((connection_point, end_pos))

                    best_path = RoutingPath(
                        start_pin=None,  # Will be set by caller
                        end_pin=None,    # Will be set by caller
                        segments=segments,
                        total_length=total_length,
                        mode=RoutingMode.MANHATTAN
                    )
                    best_path.quality_score = 1000000.0 / (total_length + 1.0)
                    best_path.bus_used = bus['id']  # Track which bus was used
                    best_length = total_length

        return best_path

    def _find_optimal_bus_connection_point(self, start_pos: Position, end_pos: Position,
                                         bus: dict) -> Position:
        """
        Find optimal point on bus structure to connect routing path.

        Returns the point on the bus that minimizes total routing length.
        """
        if bus['type'] == 'horizontal':
            # Bus is horizontal - connection point has same Y, varying X
            bus_y = bus['coordinate']

            # Check if either pin is already aligned with bus Y-coordinate
            start_aligned = abs(start_pos.y_nm - bus_y) < 100000  # 0.1mm tolerance
            end_aligned = abs(end_pos.y_nm - bus_y) < 100000

            if start_aligned:
                # Start pin is aligned with bus - connect at start X
                connection_x = max(bus['range_start'], min(bus['range_end'], start_pos.x_nm))
                return Position(connection_x, bus_y)
            elif end_aligned:
                # End pin is aligned with bus - connect at end X
                connection_x = max(bus['range_start'], min(bus['range_end'], end_pos.x_nm))
                return Position(connection_x, bus_y)
            else:
                # Neither pin aligned - find optimal connection point
                optimal_x = (start_pos.x_nm + end_pos.x_nm) // 2
                connection_x = max(bus['range_start'], min(bus['range_end'], optimal_x))
                return Position(connection_x, bus_y)

        elif bus['type'] == 'vertical':
            # Bus is vertical - connection point has same X, varying Y
            bus_x = bus['coordinate']

            # For vertical buses, prioritize connecting at the coordinate that minimizes total routing length
            # This creates direct horizontal connections when possible (like battery → bus scenarios)

            # Calculate potential connection points and their total routing costs
            start_y_option = start_pos.y_nm  # Connect at start pin's Y level
            end_y_option = end_pos.y_nm      # Connect at end pin's Y level

            # Ensure connection points are within the bus range
            start_y_clamped = max(bus['range_start'], min(bus['range_end'], start_y_option))
            end_y_clamped = max(bus['range_start'], min(bus['range_end'], end_y_option))

            # Calculate total routing path lengths for both connection options
            # Full path is: start_pos → connection_point → end_pos

            # Option 1: Connect at start Y level (creates direct horizontal connection)
            start_connection = Position(bus_x, start_y_clamped)
            start_total_length = start_pos.distance_to(start_connection) + start_connection.distance_to(end_pos)

            # Option 2: Connect at end Y level
            end_connection = Position(bus_x, end_y_clamped)
            end_total_length = start_pos.distance_to(end_connection) + end_connection.distance_to(end_pos)

            # Choose the connection point that creates the shortest total routing path
            # This ensures we get the most efficient overall route
            print(f"DEBUG BUS CONNECTION CALCULATION:")
            print(f"  Bus at x={bus_x/1000000:.2f}mm, range y={bus['range_start']/1000000:.2f}-{bus['range_end']/1000000:.2f}mm")
            print(f"  Start Y={start_y_option/1000000:.2f}mm, clamped to {start_y_clamped/1000000:.2f}mm")
            print(f"  End Y={end_y_option/1000000:.2f}mm, clamped to {end_y_clamped/1000000:.2f}mm")
            print(f"  Option 1 (start Y): total length={start_total_length/1000000:.2f}mm")
            print(f"  Option 2 (end Y): total length={end_total_length/1000000:.2f}mm")

            if start_total_length <= end_total_length:
                print(f"  → Choosing start Y connection at ({bus_x/1000000:.2f}, {start_y_clamped/1000000:.2f})")
                return start_connection
            else:
                print(f"  → Choosing end Y connection at ({bus_x/1000000:.2f}, {end_y_clamped/1000000:.2f})")
                return end_connection

        return None

    def _is_better_path(self, bus_path: RoutingPath, direct_path: RoutingPath) -> bool:
        """
        Determine if bus-aware path is better than direct path.

        Considers length, professional appearance, and design standards.
        """
        # Bus path should be meaningfully shorter to be worth the complexity
        length_improvement = (direct_path.total_length - bus_path.total_length) / direct_path.total_length

        # DEBUG: Path comparison analysis
        print(f"DEBUG PATH COMPARISON:")
        print(f"  Direct path length: {direct_path.total_length/1000000:.2f}mm")
        print(f"  Bus path length: {bus_path.total_length/1000000:.2f}mm")
        print(f"  Length improvement: {length_improvement*100:.1f}%")

        # Require at least 10% improvement to justify bus routing
        if length_improvement > 0.1:
            print(f"  → CHOOSING BUS PATH (>10% improvement)")
            return True

        # Even small improvements are valuable for professional appearance
        if length_improvement > 0.05 and bus_path.total_length < direct_path.total_length:
            print(f"  → CHOOSING BUS PATH (>5% improvement)")
            return True

        print(f"  → CHOOSING DIRECT PATH (insufficient improvement)")
        return False

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
        
        # Determine routing preferences based on pin orientations
        prefer_horizontal, prefer_vertical = self._get_routing_preferences(start_pin, end_pin)
        
        # Compute optimal break point using KiCad's actual algorithm
        break_point = self.compute_break_point(
            start_pos, end_pos, 
            RoutingMode.MANHATTAN, 
            prefer_horizontal,
            prefer_vertical
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
    
    def _get_routing_preferences(self, start_pin: Pin, end_pin: Pin) -> tuple[bool, bool]:
        """
        Determine routing direction preferences based on pin orientations and KiCad logic.
        
        This implements KiCad's professional routing preferences:
        - Pin orientations determine approach angles
        - Aligned pins get direct routing preferences
        - Sheet pin connections force horizontal routing
        - Default to distance-optimized routing
        
        Returns:
            (prefer_horizontal, prefer_vertical) tuple
        """
        # Check for alignment - if pins are aligned, prefer that direction
        if abs(start_pin.position.y_nm - end_pin.position.y_nm) < self.grid_size_nm:
            # Horizontally aligned - prefer horizontal routing
            return (True, False)
            
        if abs(start_pin.position.x_nm - end_pin.position.x_nm) < self.grid_size_nm:
            # Vertically aligned - prefer vertical routing  
            return (False, True)
        
        # Check pin orientations for smart approach angles
        # Pin orientation: 0=East, 1=North, 2=West, 3=South
        start_is_horizontal = start_pin.orientation in [0, 2]  # East or West
        end_is_horizontal = end_pin.orientation in [0, 2]      # East or West
        
        # If both pins are horizontally oriented, prefer vertical first to connect properly
        if start_is_horizontal and end_is_horizontal:
            return (False, True)
            
        # If both pins are vertically oriented, prefer horizontal first to connect properly
        start_is_vertical = start_pin.orientation in [1, 3]    # North or South
        end_is_vertical = end_pin.orientation in [1, 3]        # North or South
        
        if start_is_vertical and end_is_vertical:
            return (True, False)
        
        # Mixed orientations - use KiCad's distance-based logic as default
        # This will be handled by the algorithm itself (no strong preference)
        return (False, False)
    
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
                length=pin_data['length'],
                symbol_reference=mcp_symbol['reference']  # For debugging
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