"""
Component Boundary Detection for Smart Routing

This module provides collision detection and component avoidance capabilities
for intelligent wire routing. It integrates with KiCad's bounding box system
and implements spatial algorithms for efficient routing around components.

Based on analysis of:
- sch_symbol.cpp: GetBoundingBox() methods
- sch_rtree.h: Spatial indexing for collision detection  
- Component boundary detection mechanisms in KiCad

Phase 3 Implementation: Component Avoidance
"""

from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import math

from .smart_routing import Position, Symbol, RoutingPath


class BoundingBoxType(Enum):
    """Types of bounding boxes available from KiCad API"""
    BODY_ONLY = "body_only"        # Symbol body without pins/fields  
    BODY_PINS = "body_pins"        # Symbol body + pins
    FULL = "full"                  # Symbol body + pins + fields


@dataclass 
class BoundingBox:
    """Component bounding rectangle for collision detection"""
    top_left: Position
    bottom_right: Position
    symbol_id: str
    bbox_type: BoundingBoxType
    
    @property
    def width(self) -> int:
        return self.bottom_right.x_nm - self.top_left.x_nm
    
    @property 
    def height(self) -> int:
        return self.bottom_right.y_nm - self.top_left.y_nm
    
    @property
    def center(self) -> Position:
        return Position(
            (self.top_left.x_nm + self.bottom_right.x_nm) // 2,
            (self.top_left.y_nm + self.bottom_right.y_nm) // 2
        )
    
    def contains_point(self, point: Position) -> bool:
        """Check if point is inside bounding box"""
        return (self.top_left.x_nm <= point.x_nm <= self.bottom_right.x_nm and
                self.top_left.y_nm <= point.y_nm <= self.bottom_right.y_nm)
    
    def intersects_line(self, start: Position, end: Position) -> bool:
        """Check if line segment intersects with bounding box"""
        # Use Cohen-Sutherland line clipping algorithm
        return self._line_intersects_rectangle(start, end)
    
    def _line_intersects_rectangle(self, p1: Position, p2: Position) -> bool:
        """Cohen-Sutherland line-rectangle intersection test"""
        # Outcodes for Cohen-Sutherland algorithm
        INSIDE = 0  # 0000
        LEFT = 1    # 0001  
        RIGHT = 2   # 0010
        BOTTOM = 4  # 0100
        TOP = 8     # 1000
        
        def compute_outcode(x: int, y: int) -> int:
            code = INSIDE
            if x < self.top_left.x_nm:
                code |= LEFT
            elif x > self.bottom_right.x_nm:
                code |= RIGHT
            if y < self.top_left.y_nm:
                code |= BOTTOM
            elif y > self.bottom_right.y_nm:
                code |= TOP
            return code
        
        # Compute outcodes for both endpoints
        outcode1 = compute_outcode(p1.x_nm, p1.y_nm)
        outcode2 = compute_outcode(p2.x_nm, p2.y_nm)
        
        while True:
            if not (outcode1 | outcode2):
                # Both points inside rectangle
                return True
            elif outcode1 & outcode2:
                # Both points share an outside zone - no intersection
                return False
            else:
                # Line might intersect - clip the line
                x, y = 0, 0
                outcode_out = outcode1 if outcode1 else outcode2
                
                if outcode_out & TOP:
                    x = p1.x_nm + (p2.x_nm - p1.x_nm) * (self.bottom_right.y_nm - p1.y_nm) // (p2.y_nm - p1.y_nm)
                    y = self.bottom_right.y_nm
                elif outcode_out & BOTTOM:
                    x = p1.x_nm + (p2.x_nm - p1.x_nm) * (self.top_left.y_nm - p1.y_nm) // (p2.y_nm - p1.y_nm)
                    y = self.top_left.y_nm
                elif outcode_out & RIGHT:
                    y = p1.y_nm + (p2.y_nm - p1.y_nm) * (self.bottom_right.x_nm - p1.x_nm) // (p2.x_nm - p1.x_nm)
                    x = self.bottom_right.x_nm
                elif outcode_out & LEFT:
                    y = p1.y_nm + (p2.y_nm - p1.y_nm) * (self.top_left.x_nm - p1.x_nm) // (p2.x_nm - p1.x_nm)
                    x = self.top_left.x_nm
                
                if outcode_out == outcode1:
                    p1 = Position(x, y)
                    outcode1 = compute_outcode(p1.x_nm, p1.y_nm)
                else:
                    p2 = Position(x, y)
                    outcode2 = compute_outcode(p2.x_nm, p2.y_nm)
    
    def expand(self, margin_nm: int) -> 'BoundingBox':
        """Create expanded bounding box with clearance margin"""
        return BoundingBox(
            top_left=Position(
                self.top_left.x_nm - margin_nm,
                self.top_left.y_nm - margin_nm
            ),
            bottom_right=Position(
                self.bottom_right.x_nm + margin_nm,
                self.bottom_right.y_nm + margin_nm
            ),
            symbol_id=self.symbol_id,
            bbox_type=self.bbox_type
        )


@dataclass
class CollisionResult:
    """Result of collision detection analysis"""
    has_collision: bool
    colliding_components: List[str]
    collision_points: List[Position]
    suggested_clearance: int


class ComponentBoundaryManager:
    """
    Manages component boundaries for collision-aware routing.
    
    This class provides the spatial analysis needed for Phase 3 component
    avoidance, implementing efficient collision detection and clearance
    calculation for professional PCB routing.
    """
    
    def __init__(self, clearance_nm: int = 635000):  # 0.635mm = 25 mils default clearance
        self.clearance_nm = clearance_nm
        self.component_boundaries: Dict[str, BoundingBox] = {}
        
    def add_component_boundary(self, symbol: Symbol, bbox_type: BoundingBoxType = BoundingBoxType.BODY_PINS):
        """
        Add component boundary for collision detection.
        
        In production, this would call the new GetComponentBounds API we implemented.
        For now, we estimate based on symbol position and pin extents.
        """
        if not symbol.pins:
            # No pins - use simple box around symbol center
            margin = 1270000  # 1.27mm
            bbox = BoundingBox(
                top_left=Position(symbol.position.x_nm - margin, symbol.position.y_nm - margin),
                bottom_right=Position(symbol.position.x_nm + margin, symbol.position.y_nm + margin),
                symbol_id=symbol.id,
                bbox_type=bbox_type
            )
        else:
            # Calculate bounding box from pin extents
            min_x = min(pin.position.x_nm for pin in symbol.pins)
            max_x = max(pin.position.x_nm for pin in symbol.pins)
            min_y = min(pin.position.y_nm for pin in symbol.pins)
            max_y = max(pin.position.y_nm for pin in symbol.pins)
            
            # Add some margin for symbol body
            body_margin = 635000  # 0.635mm
            bbox = BoundingBox(
                top_left=Position(min_x - body_margin, min_y - body_margin),
                bottom_right=Position(max_x + body_margin, max_y + body_margin),
                symbol_id=symbol.id,
                bbox_type=bbox_type
            )
        
        self.component_boundaries[symbol.id] = bbox
    
    def check_path_collision(self, path: RoutingPath, exclude_pins: Set[str] = None) -> CollisionResult:
        """
        Check if routing path collides with any component boundaries.
        
        Args:
            path: The routing path to check
            exclude_pins: Pin IDs to exclude from collision (start/end pins)
        """
        exclude_pins = exclude_pins or set()
        colliding_components = []
        collision_points = []
        
        for segment_start, segment_end in path.segments:
            for symbol_id, bbox in self.component_boundaries.items():
                # Skip if this is one of our connection pins
                if symbol_id in exclude_pins:
                    continue
                    
                # Expand bounding box by clearance margin
                expanded_bbox = bbox.expand(self.clearance_nm)
                
                if expanded_bbox.intersects_line(segment_start, segment_end):
                    colliding_components.append(symbol_id)
                    # Approximate collision point as bbox center
                    collision_points.append(bbox.center)
        
        return CollisionResult(
            has_collision=len(colliding_components) > 0,
            colliding_components=list(set(colliding_components)),  # Remove duplicates
            collision_points=collision_points,
            suggested_clearance=self.clearance_nm * 2  # Suggest double clearance
        )
    
    def find_components_in_region(self, region_start: Position, region_end: Position) -> List[BoundingBox]:
        """Find all components within a rectangular region"""
        # Normalize region coordinates
        min_x = min(region_start.x_nm, region_end.x_nm)
        max_x = max(region_start.x_nm, region_end.x_nm)
        min_y = min(region_start.y_nm, region_end.y_nm)  
        max_y = max(region_start.y_nm, region_end.y_nm)
        
        region_bbox = BoundingBox(
            top_left=Position(min_x, min_y),
            bottom_right=Position(max_x, max_y),
            symbol_id="region",
            bbox_type=BoundingBoxType.FULL
        )
        
        overlapping_components = []
        for bbox in self.component_boundaries.values():
            # Check if bounding boxes overlap
            if (bbox.top_left.x_nm <= region_bbox.bottom_right.x_nm and
                bbox.bottom_right.x_nm >= region_bbox.top_left.x_nm and
                bbox.top_left.y_nm <= region_bbox.bottom_right.y_nm and
                bbox.bottom_right.y_nm >= region_bbox.top_left.y_nm):
                overlapping_components.append(bbox)
        
        return overlapping_components
    
    def suggest_detour_points(self, start: Position, end: Position, 
                            colliding_bbox: BoundingBox) -> List[Position]:
        """
        Suggest detour points to route around a colliding component.
        
        This implements basic component avoidance by suggesting waypoints
        that route around the component boundary with proper clearance.
        """
        detour_points = []
        
        # Expand component boundary by clearance
        expanded = colliding_bbox.expand(self.clearance_nm)
        
        # Determine which side of component to route around based on start/end positions
        start_to_component = colliding_bbox.center - start
        end_to_component = colliding_bbox.center - end
        
        # Calculate detour points for top/bottom routing
        if start.y_nm < colliding_bbox.center.y_nm and end.y_nm < colliding_bbox.center.y_nm:
            # Route above component
            detour_y = expanded.top_left.y_nm - self.clearance_nm
            detour_points = [
                Position(start.x_nm, detour_y),
                Position(end.x_nm, detour_y)
            ]
        elif start.y_nm > colliding_bbox.center.y_nm and end.y_nm > colliding_bbox.center.y_nm:
            # Route below component
            detour_y = expanded.bottom_right.y_nm + self.clearance_nm
            detour_points = [
                Position(start.x_nm, detour_y),
                Position(end.x_nm, detour_y)
            ]
        else:
            # Route around left or right side
            if start.x_nm < colliding_bbox.center.x_nm:
                # Route around left side
                detour_x = expanded.top_left.x_nm - self.clearance_nm
                detour_points = [
                    Position(detour_x, start.y_nm),
                    Position(detour_x, end.y_nm)
                ]
            else:
                # Route around right side
                detour_x = expanded.bottom_right.x_nm + self.clearance_nm
                detour_points = [
                    Position(detour_x, start.y_nm),
                    Position(detour_x, end.y_nm)
                ]
        
        return detour_points
    
    def get_component_clearance_zone(self, symbol_id: str) -> Optional[BoundingBox]:
        """Get expanded clearance zone for a component"""
        if symbol_id not in self.component_boundaries:
            return None
        
        bbox = self.component_boundaries[symbol_id]
        return bbox.expand(self.clearance_nm)
    
    def optimize_routing_corridor(self, start: Position, end: Position) -> Dict[str, Any]:
        """
        Analyze the routing corridor between two points for optimal path planning.
        
        Returns analysis including:
        - Obstacle density
        - Suggested routing approach (direct, detour, multi-segment)
        - Component clearance requirements
        """
        # Find components in the routing corridor
        corridor_components = self.find_components_in_region(start, end)
        
        # Calculate corridor metrics
        corridor_length = start.distance_to(end)
        obstacle_area = sum(bbox.width * bbox.height for bbox in corridor_components)
        corridor_area = abs(end.x_nm - start.x_nm) * abs(end.y_nm - start.y_nm)
        
        obstacle_density = obstacle_area / corridor_area if corridor_area > 0 else 0
        
        # Determine routing strategy
        if obstacle_density < 0.1:
            strategy = "direct"
        elif obstacle_density < 0.3:
            strategy = "simple_detour"
        else:
            strategy = "complex_multi_segment"
        
        return {
            "corridor_length_nm": corridor_length,
            "component_count": len(corridor_components),
            "obstacle_density": obstacle_density,
            "suggested_strategy": strategy,
            "clearance_required_nm": self.clearance_nm,
            "components_in_path": [bbox.symbol_id for bbox in corridor_components]
        }


class AdvancedCollisionDetector:
    """
    Advanced collision detection for Phase 3+ implementation.
    
    This class will implement sophisticated spatial algorithms for
    high-performance collision detection in complex schematics.
    """
    
    def __init__(self):
        self.spatial_index = {}  # Future: R-tree or similar spatial index
        
    def build_spatial_index(self, components: List[Symbol]):
        """Build spatial index for fast collision queries"""
        # Future implementation: R-tree spatial indexing
        # For now, simple dictionary indexing
        pass
        
    def fast_collision_check(self, path: RoutingPath) -> bool:
        """Ultra-fast collision detection using spatial indexing"""
        # Future implementation for large schematics
        return False


# Factory functions for integration
def create_boundary_manager(clearance_nm: int = 635000) -> ComponentBoundaryManager:
    """Create component boundary manager with specified clearance"""
    return ComponentBoundaryManager(clearance_nm)


def integrate_with_kicad_api(symbols_data: List[Dict[str, Any]], 
                           boundary_manager: ComponentBoundaryManager):
    """
    Integrate component boundaries with KiCad API data.
    
    This function would call our new GetComponentBounds API for each symbol
    to get precise bounding box information from KiCad.
    """
    # Future integration with GetComponentBounds API
    # For now, use symbol pin data to estimate boundaries
    for symbol_data in symbols_data:
        # Convert to Symbol object (reuse from smart_routing module)
        from .smart_routing import SmartRoutingMCPIntegration
        integration = SmartRoutingMCPIntegration()
        symbol = integration.convert_mcp_symbol_to_routing_symbol(symbol_data)
        
        # Add to boundary manager
        boundary_manager.add_component_boundary(symbol)


# Example usage
if __name__ == "__main__":
    # Test component boundary detection
    manager = ComponentBoundaryManager()
    
    # Create test component
    from .smart_routing import Symbol, Pin, Position
    
    test_symbol = Symbol(
        id="test_component",
        reference="R1", 
        value="1k",
        position=Position(100000000, 100000000),
        orientation_degrees=0,
        pins=[
            Pin("pin1", "1", "1", Position(95000000, 100000000), 0, 4, 25400),
            Pin("pin2", "2", "2", Position(105000000, 100000000), 2, 4, 25400)
        ]
    )
    
    manager.add_component_boundary(test_symbol)
    
    # Test collision detection
    from .smart_routing import RoutingPath, RoutingMode
    
    test_path = RoutingPath(
        start_pin=test_symbol.pins[0],
        end_pin=test_symbol.pins[1],
        segments=[(Position(90000000, 100000000), Position(110000000, 100000000))],
        total_length=20000000,
        mode=RoutingMode.MANHATTAN
    )
    
    result = manager.check_path_collision(test_path, exclude_pins={test_symbol.id})
    print(f"Collision Detection Test:")
    print(f"  Has Collision: {result.has_collision}")
    print(f"  Colliding Components: {result.colliding_components}")
    print(f"  Suggested Clearance: {result.suggested_clearance} nm")