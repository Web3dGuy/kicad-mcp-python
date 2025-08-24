# KiCad MCP Server - Complete Capabilities Documentation

## Overview

The KiCad MCP (Model Context Protocol) server is a sophisticated bridge between AI models and KiCad, the open-source PCB design software. It provides programmatic access to KiCad's functionality through a well-structured API that enables AI assistants to create, modify, analyze, and visualize PCB designs.

## Architecture

### Core Components

1. **FastMCP Server**: Built on the Model Context Protocol foundation for reliable client-server communication
2. **KiCad Integration**: Uses the official `kicad-python` library and KiCad's IPC-API for stable communication
3. **Protocol Buffer System**: Handles data conversion between MCP requests and KiCad's internal format
4. **Action Flow Manager**: Orchestrates multi-step operations with automatic verification
5. **Visual Feedback System**: Generates PCB screenshots for AI model context
6. **Graceful Shutdown**: Comprehensive cleanup and resource management

### Supported KiCad Objects

The server supports manipulation of the following PCB elements:

- **Arc**: Curved traces and graphical elements
- **BoardGraphicShape**: Board outline and graphical shapes
- **BoardText**: Text labels on the PCB
- **BoardTextBox**: Text boxes with formatting
- **Dimension**: Measurement annotations
- **Field**: Component field text
- **Footprint3DModel**: 3D model associations
- **FootprintInstance**: Component footprints/instances
- **Net**: Electrical networks
- **Pad**: Component connection pads
- **Track**: Electrical traces
- **Via**: Layer-to-layer connections
- **Zone**: Copper fill areas

## Primary Capabilities

### 1. PCB Object Manipulation

#### Create Operations
- **Entry Point**: `create_item_step_1()`
- **Type Selection**: `create_item_step_2(item_type)`
- **Object Creation**: `create_item_step_3(item_type, args)`

**Supported Creation Parameters**:
- Arc: `start`, `end`, `center`, `angle`
- Track: `start`, `end` positions
- Via: `position`
- Footprint: `position`, `definition`
- Zone: `name`, `layers`, `outline`
- Text: `text` content
- And many more...

#### Edit Operations
- **Entry Point**: `edit_item_step_1()`
- **Item Listing**: `edit_item_step_2(item_type)`
- **Modification**: `edit_item_step_3(item_id, args)`

**Edit Capabilities**:
- Modify any object property except position/rotation (use move operations instead)
- Update text content, dimensions, layer assignments
- Change electrical properties like net assignments
- Modify visual properties like line thickness, colors

#### Move Operations
- **Entry Point**: `move_item_step_1()`
- **Item Selection**: `move_item_step_2(item_type)`
- **Position/Rotation**: `move_item_step_3(item_id, args)`

**Movement Parameters**:
- **For Tracks**: `start` and `end` position adjustments
- **For Other Objects**: `xy_nm` (position offset) and `angle` (rotation)
- Supports relative positioning and absolute angle setting

#### Remove Operations
- **Single Function**: `remove_item_step_1(item_ids)`
- **Batch Removal**: Accepts list of item IDs for efficient bulk operations

### 2. PCB Analysis and Inspection

#### Board Status Analysis
- **Function**: `get_board_status()`
- **Returns**: Complete board state with visual representation
- **Output**: 
  - Dictionary of all board items by type
  - High-quality JPEG screenshot of current PCB state
  - Error reporting for unsupported item types

#### Item Querying
- **Function**: `get_items_by_type(item_type)`
- **Returns**: Dictionary mapping item IDs to item objects
- **Use Cases**: Finding specific components, analyzing connectivity

#### Type Information
- **Function**: `get_item_type_args_hint(item_type)`
- **Returns**: Schema information for creating/editing items
- **Contains**: Required arguments, optional parameters, data types

### 3. Visual Feedback System

#### Screenshot Generation
- **Technology**: KiCad CLI → SVG → Cairo → JPEG conversion
- **Layers**: Configurable layer visibility (F.Cu, B.Cu, SilkS, Mask, Edge.Cuts)
- **Quality**: High-resolution images optimized for AI model consumption
- **Storage**: Automatic timestamped screenshot archiving
- **Format**: Base64-encoded JPEG with MCP ImageContent wrapper

#### Pre/Post Operation Verification
- **Automatic Screenshots**: Before and after each modification operation
- **Visual Confirmation**: AI models can verify successful operations
- **Error Detection**: Visual diff capabilities for operation validation

### 4. Data Conversion and Protocol Handling

#### Protocol Buffer Integration
- **Bi-directional Conversion**: MCP JSON ↔ Protocol Buffer ↔ KiCad Objects
- **Type Safety**: Strong typing with automatic validation
- **Schema Discovery**: Runtime introspection of KiCad data structures
- **Error Handling**: Graceful handling of unsupported or malformed data

#### Object Factory System
- **Dynamic Creation**: Runtime object instantiation from type strings
- **Wrapper Classes**: Clean abstraction over raw protocol buffers
- **Validation**: Automatic validation of required vs optional parameters

### 5. Workflow Management

#### Action Flow Manager
- **Step Sequencing**: Guides users through multi-step operations
- **State Management**: Maintains operation context across steps
- **Error Recovery**: Graceful handling of operation failures
- **Next Action Guidance**: Automatic suggestion of follow-up operations

#### Tool Registration System
- **Automatic Discovery**: Dynamic tool registration with FastMCP
- **Documentation**: Automatic extraction of function docstrings
- **Parameter Introspection**: Automatic parameter schema generation
- **Context Management**: Proper MCP context handling

### 6. Environment Integration

#### KiCad CLI Integration
- **Path Configuration**: Flexible CLI path configuration via environment variables
- **Multiple PCB Support**: Access to multiple PCB files simultaneously
- **Layer Control**: Fine-grained layer visibility control
- **Export Options**: Multiple export formats and quality settings

#### File Management
- **Auto-Save**: Automatic saving after modifications
- **Disk Sync**: Force-write operations for CLI compatibility
- **Backup**: Timestamped screenshot archives
- **Cleanup**: Temporary file management

### 7. Error Handling and Reliability

#### Comprehensive Error Handling
- **Operation Validation**: Pre-flight checks before modifications
- **Graceful Degradation**: Partial success reporting
- **Detailed Error Messages**: Specific error types and descriptions
- **Recovery Suggestions**: Actionable error resolution guidance

#### Resource Management
- **Memory Management**: Proper cleanup of KiCad resources
- **Connection Pooling**: Efficient IPC connection management
- **Signal Handling**: Graceful shutdown on system signals
- **Cleanup Registry**: Automatic resource cleanup on exit

## Advanced Features

### 1. Multi-Object Operations
- **Batch Processing**: Efficient handling of multiple objects
- **Transaction-like Behavior**: All-or-nothing operation semantics
- **Performance Optimization**: Reduced IPC overhead for bulk operations

### 2. Visual Analysis Integration
- **Screenshot Comparison**: Before/after visual analysis
- **Layer-specific Views**: Targeted analysis of specific PCB layers
- **Annotation Support**: Visual markup and measurement tools

### 3. Development and Debugging Support
- **Verbose Logging**: Comprehensive operation logging
- **Debug Screenshots**: Intermediate state visualization
- **Command Echo**: CLI command logging for troubleshooting
- **Performance Metrics**: Operation timing and resource usage

## Configuration Requirements

### Environment Variables
```bash
KICAD_CLI_PATH=/path/to/kicad-cli
PCB_PATHS=/path/to/project1.kicad_pcb,/path/to/project2.kicad_pcb
```

### Dependencies
- **Core**: `kicad-python`, `mcp`, `python-dotenv`
- **Image Processing**: `cairosvg`, `PIL`
- **Protocol**: `protobuf`, `google.protobuf`

### KiCad Integration
- **IPC Server**: Must be enabled in KiCad (Tools → External Plugin → Start Server)
- **Version Compatibility**: Designed for KiCad 9.0+ with backward compatibility
- **CLI Access**: Requires KiCad CLI for screenshot generation

## Usage Patterns

### 1. Interactive PCB Design
```
1. get_board_status() - Analyze current state
2. create_item_step_* - Add new components
3. get_board_status() - Verify changes
4. move_item_step_* - Position components
5. get_board_status() - Final verification
```

### 2. Automated PCB Analysis
```
1. get_board_status() - Full board analysis
2. get_items_by_type() - Specific component analysis
3. Visual inspection via screenshots
4. Report generation
```

### 3. Batch Modifications
```
1. get_items_by_type() - Identify targets
2. Multiple edit_item_step_3() calls
3. get_board_status() - Verify all changes
```

## Future Roadmap

### Planned Enhancements
- **Schematic Support**: Integration with KiCad's schematic editor
- **Multi-Item Selection**: Simultaneous editing of multiple objects
- **Workflow Templates**: Pre-defined operation sequences
- **Advanced Analysis**: DRC integration, signal integrity analysis
- **Collaboration Features**: Multi-user design support

### Performance Improvements
- **Caching**: Intelligent caching of board state
- **Streaming**: Large board support via streaming operations
- **Parallelization**: Concurrent operation processing
- **Memory Optimization**: Reduced memory footprint for large designs

## Technical Notes

### Version Compatibility
- **KiCad 9.0.4+**: Full feature support with `get_items_by_id`
- **KiCad 9.0.0-9.0.3**: Compatible with fallback implementations
- **Older Versions**: Limited support, some features unavailable

### Performance Characteristics
- **Operation Latency**: ~100-500ms per operation depending on complexity
- **Screenshot Generation**: ~1-3 seconds depending on board size
- **Memory Usage**: Scales with board complexity, typically <100MB
- **Concurrent Operations**: Thread-safe design supports multiple simultaneous operations

### Security Considerations
- **File Access**: Restricted to configured PCB_PATHS
- **Command Execution**: Limited to KiCad CLI operations
- **Resource Limits**: Built-in protection against resource exhaustion
- **Input Validation**: Comprehensive validation of all inputs

This MCP server represents a significant advancement in AI-assisted PCB design, providing unprecedented programmatic access to KiCad's capabilities while maintaining reliability, safety, and ease of use.
