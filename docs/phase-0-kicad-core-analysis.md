# Phase 0: KiCad Core Analysis - Actual Implementation

## Critical Distinction

- **`eeschema/api/`**: Our custom API implementation (NOT KiCad core)
- **KiCad Core**: The actual schematic editor implementation in `eeschema/tools/`, `eeschema/sch_*.cpp`

## KiCad Core Wire Routing Analysis

### 1. Wire Drawing Tool (`sch_line_wire_bus_tool.cpp`)

**Key Functions:**
- `doDrawSegments()` (line 607-1200+): Main wire drawing loop
- `computeBreakPoint()` (line 470-604): Calculates Manhattan routing break points
- `trimSegmentToGrid()`: Grid alignment

**Critical Finding: NO COLLISION DETECTION**
```cpp
// Line 607-756: Main drawing loop
int SCH_LINE_WIRE_BUS_TOOL::doDrawSegments(...) {
    // NO collision checking with components
    // Directly draws wires based on cursor position
    // Uses grid snapping but NO obstacle avoidance
}
```

**What KiCad DOES:**
- Grid snapping via `EE_GRID_HELPER`
- Manhattan routing (90-degree angles)
- Sheet pin connection awareness
- Wire merging for overlapping segments

**What KiCad DOESN'T DO:**
- Component collision detection
- Pathfinding around obstacles
- Automated routing
- Wire optimization for minimal crossings

### 2. Grid Helper (`ee_grid_helper.cpp`)

**Key Functions:**
- `BestSnapAnchor()` (line 169-275): Finds best snap point
- `computeAnchors()` (line 468-576): Collects snap anchors from items
- Grid alignment with override support

**Snap Point Types:**
```cpp
enum ANCHOR_FLAGS {
    CORNER    = 0x01,
    OUTLINE   = 0x02,
    SNAPPABLE = 0x04,
    ORIGIN    = 0x08,
    VERTICAL  = 0x10,
    HORIZONTAL= 0x20
};
```

**Finding:** KiCad snaps to pins, junctions, and wire ends but doesn't avoid components.

### 3. Component Boundaries (`sch_symbol.cpp`)

**Bounding Box Methods:**
```cpp
// Line 1852: Core bounding box calculation
BOX2I SCH_SYMBOL::doGetBoundingBox(bool aIncludePins, bool aIncludeFields) {
    // Gets body bounds from library symbol
    bBox = m_part->GetBodyBoundingBox(m_unit, m_bodyStyle, aIncludePins, false);
    // Transforms based on symbol orientation
    bBox = m_transform.TransformCoordinate(bBox);
    // Optionally includes field text
}

// Line 1880: Body only
BOX2I GetBodyBoundingBox() const;

// Line 1894: Body + pins
BOX2I GetBodyAndPinsBoundingBox() const;

// Line 1900: Full bounds with fields
const BOX2I GetBoundingBox() const;
```

**Usage in Core:**
- Hit testing for selection (line 2455)
- Drawing/plotting boundaries
- NOT used for wire routing decisions

### 4. Collision/Intersection Detection

**Found Uses:**
```cpp
// Line 438: Find overlapping items for dangling ends
screen->Items().Overlapping(m_busUnfold.entry->GetBoundingBox())

// Line 455: Find sheets at position
screen->Items().Overlapping(SCH_SHEET_T, aPosition)

// Line 1182: Merge overlapping wire segments
line->MergeOverlap(screen, next_line, false)
```

**Critical:** These are for UI operations and cleanup, NOT routing decisions.

### 5. No Automated Routing in KiCad Core

**Search Results:**
- No "autoroute" functionality in schematic editor
- No pathfinding algorithms
- No A* or similar routing algorithms
- Manual wire drawing only

## Key Insights from Core Analysis

### What We Can Learn from KiCad:

1. **Grid System:**
   - Default 1.27mm (50 mil) grid
   - Grid overrides for wires vs graphics
   - Snap to pins, junctions, wire ends

2. **Wire Drawing Pattern:**
   - User-driven manual routing
   - Manhattan mode with break points
   - 45-degree mode support
   - Free drawing mode

3. **Component Boundaries:**
   - Three levels: body, body+pins, full
   - Transformed based on rotation
   - Available but unused for routing

### What's Missing in KiCad Core:

1. **No Collision Avoidance:**
   - Wires drawn through components
   - No obstacle detection
   - No automated detours

2. **No Pathfinding:**
   - No A* or similar algorithms
   - No route optimization
   - Manual only

3. **No Smart Routing:**
   - No pin approach angles
   - No bus-aware routing
   - No quality metrics

## Our Implementation vs KiCad Core

### What We've Added (in our API):
- `GetComponentBounds` API endpoint
- `GetGridAnchors` API endpoint
- `GetConnectionPoints` API endpoint
- Smart routing workflow

### What We Haven't Used:
- Our own `GetComponentBounds` API
- Grid anchors for routing
- Connection points for bus routing

### What KiCad Doesn't Have:
- Automated routing
- Collision detection for wires
- Pathfinding algorithms

## Implications for Our Implementation

### 1. We're Not Missing KiCad Features
KiCad doesn't have smart routing - we're building something NEW.

### 2. Our APIs Are Correct
We've implemented the right APIs (`GetComponentBounds`, etc.) - we just need to USE them.

### 3. A* Pathfinding Is The Right Choice
Since KiCad has no pathfinding, adding A* is a pure enhancement.

### 4. Grid Compatibility Is Solved
Our grid alignment already matches KiCad's system.

## Recommended Approach

### Use What KiCad Does Well:
- Grid snapping logic (already ported)
- Manhattan break points (already implemented)
- Wire merging (can adopt)

### Add What KiCad Lacks:
- Collision detection using our `GetComponentBounds`
- A* pathfinding for obstacle avoidance
- Bus-aware routing optimization
- Quality scoring for paths

### Implementation Priority:
1. **Immediate:** Use our `GetComponentBounds` API
2. **Next:** Add A* pathfinding with collision grid
3. **Then:** Optimize with bus awareness
4. **Future:** Batch wire creation for performance

## Conclusion

KiCad's schematic editor has **NO automated routing or collision detection**. Our smart routing implementation is not replacing KiCad functionality - it's adding entirely new capabilities. The core issue is that we built the right APIs but haven't integrated them into the routing algorithm. The solution is straightforward: use our APIs + add A* pathfinding.