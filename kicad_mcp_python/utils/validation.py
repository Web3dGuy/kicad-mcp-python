"""
Validation utilities for KiCad MCP operations.

This module provides validation functions to prevent silent data corruption
and improve error handling in the MCP layer before calls reach the KiCad API.

Based on comprehensive error analysis from Section 5 of the schematic API
optimization task, this addresses:
- Coordinate clamping issues (extreme coordinates silently clamped)
- Zero-length wire acceptance
- Negative wire width acceptance
- Empty label text handling
- Context-dependent error messages
"""

from typing import Dict, Any, List, Optional, Tuple
import math


class ValidationError(Exception):
    """Custom exception for validation failures with helpful context."""

    def __init__(self, message: str, field: str = None, value: Any = None, suggestions: List[str] = None):
        self.field = field
        self.value = value
        self.suggestions = suggestions or []
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for MCP responses."""
        result = {"error": str(self)}
        if self.field:
            result["invalid_field"] = self.field
        if self.value is not None:
            result["invalid_value"] = self.value
        if self.suggestions:
            result["suggestions"] = self.suggestions
        return result


class CoordinateValidator:
    """Validates coordinate values and ranges."""

    # KiCad coordinate limits (conservative bounds based on error analysis)
    # These prevent the silent clamping observed in testing
    MAX_COORD_NM = 100_000_000_000_000  # 100m in nanometers (very conservative)
    MIN_COORD_NM = -100_000_000_000_000

    # Practical schematic bounds (more realistic for error messages)
    PRACTICAL_MAX_MM = 1000  # 1m schematic sheet
    PRACTICAL_MIN_MM = -1000

    @classmethod
    def validate_coordinate(cls, value: int, field_name: str) -> None:
        """
        Validate a single coordinate value.

        Args:
            value: Coordinate value in nanometers
            field_name: Name of the field for error reporting

        Raises:
            ValidationError: If coordinate is out of bounds
        """
        if not isinstance(value, (int, float)):
            raise ValidationError(
                f"{field_name} must be a number, got {type(value).__name__}",
                field=field_name,
                value=value,
                suggestions=["Ensure coordinates are numeric values in nanometers"]
            )

        value = int(value)  # Convert to int for consistency

        if not (cls.MIN_COORD_NM <= value <= cls.MAX_COORD_NM):
            value_mm = value / 1_000_000
            raise ValidationError(
                f"{field_name} coordinate {value_mm:.1f}mm ({value}nm) exceeds valid range "
                f"({cls.PRACTICAL_MIN_MM}mm to {cls.PRACTICAL_MAX_MM}mm)",
                field=field_name,
                value=value,
                suggestions=[
                    f"Use coordinates between {cls.PRACTICAL_MIN_MM}mm and {cls.PRACTICAL_MAX_MM}mm",
                    "Convert coordinates to nanometers (1mm = 1,000,000nm)",
                    "Check if coordinates are in correct units (should be nanometers, not micrometers)"
                ]
            )

    @classmethod
    def validate_position(cls, position: Dict[str, Any], field_name: str = "position") -> Dict[str, int]:
        """
        Validate a position dictionary with x_nm and y_nm coordinates.

        Args:
            position: Dictionary with x_nm and y_nm keys
            field_name: Name of the field for error reporting

        Returns:
            Validated position with integer coordinates

        Raises:
            ValidationError: If position structure or values are invalid
        """
        if not isinstance(position, dict):
            raise ValidationError(
                f"{field_name} must be a dictionary with x_nm and y_nm keys",
                field=field_name,
                value=position,
                suggestions=["Use format: {'x_nm': 50800000, 'y_nm': 50800000}"]
            )

        required_keys = ["x_nm", "y_nm"]
        missing_keys = [key for key in required_keys if key not in position]
        if missing_keys:
            raise ValidationError(
                f"{field_name} missing required keys: {missing_keys}",
                field=field_name,
                value=position,
                suggestions=[f"Include all required keys: {required_keys}"]
            )

        # Validate each coordinate
        cls.validate_coordinate(position["x_nm"], f"{field_name}.x_nm")
        cls.validate_coordinate(position["y_nm"], f"{field_name}.y_nm")

        return {
            "x_nm": int(position["x_nm"]),
            "y_nm": int(position["y_nm"])
        }


class WireValidator:
    """Validates wire geometry and parameters."""

    MIN_WIRE_LENGTH_NM = 1_000_000  # 1mm minimum wire length
    MAX_WIRE_WIDTH_NM = 10_000_000  # 10mm maximum wire width
    MIN_WIRE_WIDTH_NM = 0  # 0 = use default width

    @classmethod
    def validate_wire_geometry(cls, start_pos: Dict[str, Any], end_pos: Dict[str, Any]) -> Tuple[Dict[str, int], Dict[str, int], float]:
        """
        Validate wire start and end positions and calculate geometry.

        Args:
            start_pos: Starting position dictionary
            end_pos: Ending position dictionary

        Returns:
            Tuple of (validated_start, validated_end, length_mm)

        Raises:
            ValidationError: If wire geometry is invalid
        """
        # Validate position structures
        start = CoordinateValidator.validate_position(start_pos, "start_point")
        end = CoordinateValidator.validate_position(end_pos, "end_point")

        # Check for zero-length wire (identical start/end points)
        if start["x_nm"] == end["x_nm"] and start["y_nm"] == end["y_nm"]:
            raise ValidationError(
                "Wire start and end points are identical (zero-length wire)",
                field="wire_geometry",
                value={"start": start, "end": end},
                suggestions=[
                    "Ensure start_point and end_point are different",
                    "Check if coordinates are intended to create a visible wire",
                    f"Minimum recommended wire length: {cls.MIN_WIRE_LENGTH_NM/1_000_000}mm"
                ]
            )

        # Calculate wire length
        dx = end["x_nm"] - start["x_nm"]
        dy = end["y_nm"] - start["y_nm"]
        length_nm = math.sqrt(dx*dx + dy*dy)
        length_mm = length_nm / 1_000_000

        # Check minimum wire length (warn, don't error for very short wires)
        if length_nm < cls.MIN_WIRE_LENGTH_NM:
            raise ValidationError(
                f"Wire length {length_mm:.3f}mm is very short and may not be visible",
                field="wire_length",
                value=length_mm,
                suggestions=[
                    f"Recommended minimum wire length: {cls.MIN_WIRE_LENGTH_NM/1_000_000}mm",
                    "Verify coordinates are correct and in nanometers",
                    "Consider if this wire segment is necessary"
                ]
            )

        return start, end, length_mm

    @classmethod
    def validate_wire_width(cls, width: Any) -> int:
        """
        Validate wire width parameter.

        Args:
            width: Wire width in nanometers

        Returns:
            Validated width as integer

        Raises:
            ValidationError: If width is invalid
        """
        if width is None:
            return 0  # Default width

        if not isinstance(width, (int, float)):
            raise ValidationError(
                f"Wire width must be a number, got {type(width).__name__}",
                field="width",
                value=width,
                suggestions=["Use 0 for default width, or specify width in nanometers"]
            )

        width = int(width)

        if width < cls.MIN_WIRE_WIDTH_NM:
            raise ValidationError(
                f"Wire width {width}nm cannot be negative",
                field="width",
                value=width,
                suggestions=[
                    "Use 0 for default width",
                    "Specify positive width in nanometers (e.g., 150000 for 0.15mm)"
                ]
            )

        if width > cls.MAX_WIRE_WIDTH_NM:
            width_mm = width / 1_000_000
            max_mm = cls.MAX_WIRE_WIDTH_NM / 1_000_000
            raise ValidationError(
                f"Wire width {width_mm}mm exceeds maximum {max_mm}mm",
                field="width",
                value=width,
                suggestions=[
                    f"Use width between 0 and {max_mm}mm",
                    "Check if width is in correct units (should be nanometers)"
                ]
            )

        return width


class TextValidator:
    """Validates text content and parameters."""

    MAX_TEXT_LENGTH = 1000  # Maximum text length (conservative)
    MIN_TEXT_LENGTH = 1     # Minimum text length (prevent empty)

    @classmethod
    def validate_text_content(cls, text: Any, field_name: str = "text", allow_empty: bool = False) -> str:
        """
        Validate text content for labels and annotations.

        Args:
            text: Text content (string or dict with 'text' key)
            field_name: Name of the field for error reporting
            allow_empty: Whether to allow empty text

        Returns:
            Validated text content as string

        Raises:
            ValidationError: If text is invalid
        """
        # Handle different text input formats
        if isinstance(text, str):
            text_content = text
        elif isinstance(text, dict) and "text" in text:
            text_content = text["text"]
        else:
            raise ValidationError(
                f"{field_name} must be a string or dict with 'text' key",
                field=field_name,
                value=text,
                suggestions=[
                    "Use string format: 'VCC'",
                    "Use dict format: {'text': 'VCC'}"
                ]
            )

        if not isinstance(text_content, str):
            raise ValidationError(
                f"{field_name} content must be a string, got {type(text_content).__name__}",
                field=field_name,
                value=text_content,
                suggestions=["Ensure text content is a string"]
            )

        # Check for empty text
        if not allow_empty and len(text_content.strip()) == 0:
            raise ValidationError(
                f"{field_name} cannot be empty",
                field=field_name,
                value=text_content,
                suggestions=[
                    "Provide meaningful label text (e.g., 'VCC', 'GND', 'RESET')",
                    "Use descriptive names for net labels",
                    "Remove label if no text is needed"
                ]
            )

        # Check text length
        if len(text_content) > cls.MAX_TEXT_LENGTH:
            raise ValidationError(
                f"{field_name} length {len(text_content)} exceeds maximum {cls.MAX_TEXT_LENGTH}",
                field=field_name,
                value=len(text_content),
                suggestions=[
                    f"Limit text to {cls.MAX_TEXT_LENGTH} characters",
                    "Use shorter, more concise label names"
                ]
            )

        return text_content.strip()


class ParameterValidator:
    """Validates general parameter structures and types."""

    @classmethod
    def validate_required_parameters(cls, args: Dict[str, Any], required: List[str], function_name: str = "function") -> None:
        """
        Validate that all required parameters are present.

        Args:
            args: Parameter dictionary
            required: List of required parameter names
            function_name: Name of the function for error reporting

        Raises:
            ValidationError: If required parameters are missing
        """
        if not isinstance(args, dict):
            raise ValidationError(
                f"{function_name} arguments must be a dictionary",
                field="args",
                value=args,
                suggestions=["Pass parameters as a dictionary"]
            )

        missing = [param for param in required if param not in args]
        if missing:
            raise ValidationError(
                f"{function_name} missing required parameters: {missing}",
                field="required_parameters",
                value=missing,
                suggestions=[
                    f"Include all required parameters: {required}",
                    f"Provided parameters: {list(args.keys())}"
                ]
            )

    @classmethod
    def validate_item_type(cls, item_type: str, valid_types: List[str], function_name: str = "function") -> str:
        """
        Validate item type parameter.

        Args:
            item_type: Type of item to validate
            valid_types: List of valid item types
            function_name: Name of the function for error reporting

        Returns:
            Validated item type

        Raises:
            ValidationError: If item type is invalid
        """
        if not isinstance(item_type, str):
            raise ValidationError(
                f"{function_name} item_type must be a string, got {type(item_type).__name__}",
                field="item_type",
                value=item_type,
                suggestions=["Specify item_type as a string"]
            )

        if item_type not in valid_types:
            raise ValidationError(
                f"{function_name} invalid item_type '{item_type}'",
                field="item_type",
                value=item_type,
                suggestions=[
                    f"Use one of: {valid_types}",
                    "Check spelling and case sensitivity"
                ]
            )

        return item_type


def validate_wire_creation_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive validation for wire creation arguments.

    Args:
        args: Wire creation arguments

    Returns:
        Validated and normalized arguments

    Raises:
        ValidationError: If any validation fails
    """
    try:
        # Validate required parameters
        ParameterValidator.validate_required_parameters(
            args, ["start_point", "end_point"], "draw_wire"
        )

        # Validate wire geometry
        start, end, length_mm = WireValidator.validate_wire_geometry(
            args["start_point"], args["end_point"]
        )

        # Validate wire width (optional)
        width = WireValidator.validate_wire_width(args.get("width", 0))

        return {
            "start_point": start,
            "end_point": end,
            "width": width,
            "validated": True,
            "length_mm": length_mm
        }

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(
            f"Unexpected error during wire validation: {str(e)}",
            field="validation",
            suggestions=["Check parameter format and values"]
        )


def validate_label_creation_args(args: Dict[str, Any], label_type: str) -> Dict[str, Any]:
    """
    Comprehensive validation for label creation arguments.

    Args:
        args: Label creation arguments
        label_type: Type of label ("LocalLabel", "GlobalLabel", etc.)

    Returns:
        Validated and normalized arguments

    Raises:
        ValidationError: If any validation fails
    """
    try:
        # Validate required parameters
        ParameterValidator.validate_required_parameters(
            args, ["position", "text"], f"create_{label_type}"
        )

        # Validate position
        position = CoordinateValidator.validate_position(args["position"])

        # Validate text content
        text_content = TextValidator.validate_text_content(args["text"], "label_text")

        # Validate label type
        valid_types = ["LocalLabel", "GlobalLabel", "HierLabel"]
        validated_type = ParameterValidator.validate_item_type(
            label_type, valid_types, "create_label"
        )

        return {
            "position": position,
            "text": text_content,
            "label_type": validated_type,
            "validated": True
        }

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(
            f"Unexpected error during label validation: {str(e)}",
            field="validation",
            suggestions=["Check parameter format and values"]
        )


def validate_junction_creation_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive validation for junction creation arguments.

    Args:
        args: Junction creation arguments

    Returns:
        Validated and normalized arguments

    Raises:
        ValidationError: If any validation fails
    """
    try:
        # Validate required parameters
        ParameterValidator.validate_required_parameters(
            args, ["position"], "create_junction"
        )

        # Validate position
        position = CoordinateValidator.validate_position(args["position"])

        return {
            "position": position,
            "validated": True
        }

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(
            f"Unexpected error during junction validation: {str(e)}",
            field="validation",
            suggestions=["Check parameter format and values"]
        )