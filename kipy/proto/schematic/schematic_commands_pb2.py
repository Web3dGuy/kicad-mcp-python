"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
_sym_db = _symbol_database.Default()
from ..common.types import base_types_pb2 as common_dot_types_dot_base__types__pb2
from ..common.types import enums_pb2 as common_dot_types_dot_enums__pb2
from google.protobuf import any_pb2 as google_dot_protobuf_dot_any__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n"schematic/schematic_commands.proto\x12\x18kiapi.schematic.commands\x1a\x1dcommon/types/base_types.proto\x1a\x18common/types/enums.proto\x1a\x19google/protobuf/any.proto"L\n\x10GetSchematicInfo\x128\n\tschematic\x18\x01 \x01(\x0b2%.kiapi.common.types.DocumentSpecifier"\x80\x01\n\x15SchematicInfoResponse\x12\x14\n\x0cproject_name\x18\x01 \x01(\t\x12\x13\n\x0bsheet_count\x18\x02 \x01(\x05\x12\x14\n\x0csymbol_count\x18\x03 \x01(\x05\x12\x11\n\tnet_count\x18\x04 \x01(\x05\x12\x13\n\x0bsheet_names\x18\x05 \x03(\t"\xad\x01\n\x11GetSchematicItems\x128\n\tschematic\x18\x01 \x01(\x0b2%.kiapi.common.types.DocumentSpecifier\x12*\n\x08item_ids\x18\x02 \x03(\x0b2\x18.kiapi.common.types.KIID\x122\n\x05types\x18\x03 \x03(\x0e2#.kiapi.common.types.KiCadObjectType"U\n\x19GetSchematicItemsResponse\x12#\n\x05items\x18\x01 \x03(\x0b2\x14.google.protobuf.Any\x12\x13\n\x0btotal_count\x18\x02 \x01(\x05"u\n\x14CreateSchematicItems\x128\n\tschematic\x18\x01 \x01(\x0b2%.kiapi.common.types.DocumentSpecifier\x12#\n\x05items\x18\x02 \x03(\x0b2\x14.google.protobuf.Any"]\n\x1cCreateSchematicItemsResponse\x12-\n\x0bcreated_ids\x18\x01 \x03(\x0b2\x18.kiapi.common.types.KIID\x12\x0e\n\x06errors\x18\x02 \x03(\tb\x06proto3')
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'schematic.schematic_commands_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _GETSCHEMATICINFO._serialized_start = 148
    _GETSCHEMATICINFO._serialized_end = 224
    _SCHEMATICINFORESPONSE._serialized_start = 227
    _SCHEMATICINFORESPONSE._serialized_end = 355
    _GETSCHEMATICITEMS._serialized_start = 358
    _GETSCHEMATICITEMS._serialized_end = 531
    _GETSCHEMATICITEMSRESPONSE._serialized_start = 533
    _GETSCHEMATICITEMSRESPONSE._serialized_end = 618
    _CREATESCHEMATICITEMS._serialized_start = 620
    _CREATESCHEMATICITEMS._serialized_end = 737
    _CREATESCHEMATICITEMSRESPONSE._serialized_start = 739
    _CREATESCHEMATICITEMSRESPONSE._serialized_end = 832