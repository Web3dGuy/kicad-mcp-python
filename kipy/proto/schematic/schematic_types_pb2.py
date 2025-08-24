"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
_sym_db = _symbol_database.Default()
from ..common.types import base_types_pb2 as common_dot_types_dot_base__types__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1fschematic/schematic_types.proto\x12\x15kiapi.schematic.types\x1a\x1dcommon/types/base_types.proto"\xb8\x01\n\x04Line\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12*\n\x05start\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12(\n\x03end\x18\x03 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x124\n\x05layer\x18\x04 \x01(\x0e2%.kiapi.schematic.types.SchematicLayer".\n\x04Text\x12&\n\x04text\x18\x01 \x01(\x0b2\x18.kiapi.common.types.Text"\x8c\x01\n\nLocalLabel\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12-\n\x08position\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12)\n\x04text\x18\x03 \x01(\x0b2\x1b.kiapi.schematic.types.Text"\x8d\x01\n\x0bGlobalLabel\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12-\n\x08position\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12)\n\x04text\x18\x03 \x01(\x0b2\x1b.kiapi.schematic.types.Text"\x93\x01\n\x11HierarchicalLabel\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12-\n\x08position\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12)\n\x04text\x18\x03 \x01(\x0b2\x1b.kiapi.schematic.types.Text"\x90\x01\n\x0eDirectiveLabel\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12-\n\x08position\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12)\n\x04text\x18\x03 \x01(\x0b2\x1b.kiapi.schematic.types.Text"\x9b\x01\n\x08Junction\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12-\n\x08position\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12\x10\n\x08diameter\x18\x03 \x01(\x05\x12(\n\x05color\x18\x04 \x01(\x0b2\x19.kiapi.common.types.Color"\xb8\x01\n\x04Wire\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12*\n\x05start\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12(\n\x03end\x18\x03 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x124\n\x06stroke\x18\x04 \x01(\x0b2$.kiapi.common.types.StrokeAttributes"\xb7\x01\n\x03Bus\x12$\n\x02id\x18\x01 \x01(\x0b2\x18.kiapi.common.types.KIID\x12*\n\x05start\x18\x02 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x12(\n\x03end\x18\x03 \x01(\x0b2\x1b.kiapi.common.types.Vector2\x124\n\x06stroke\x18\x04 \x01(\x0b2$.kiapi.common.types.StrokeAttributes* \n\x0eSchematicLayer\x12\x0e\n\nSL_UNKNOWN\x10\x00b\x06proto3')
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'schematic.schematic_types_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _SCHEMATICLAYER._serialized_start = 1439
    _SCHEMATICLAYER._serialized_end = 1471
    _LINE._serialized_start = 90
    _LINE._serialized_end = 274
    _TEXT._serialized_start = 276
    _TEXT._serialized_end = 322
    _LOCALLABEL._serialized_start = 325
    _LOCALLABEL._serialized_end = 465
    _GLOBALLABEL._serialized_start = 468
    _GLOBALLABEL._serialized_end = 609
    _HIERARCHICALLABEL._serialized_start = 612
    _HIERARCHICALLABEL._serialized_end = 759
    _DIRECTIVELABEL._serialized_start = 762
    _DIRECTIVELABEL._serialized_end = 906
    _JUNCTION._serialized_start = 909
    _JUNCTION._serialized_end = 1064
    _WIRE._serialized_start = 1067
    _WIRE._serialized_end = 1251
    _BUS._serialized_start = 1254
    _BUS._serialized_end = 1437