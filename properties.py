import bpy

# V5.9: The map is now truly lazy. It's declared here but populated by the engine.
_datablock_creation_map = {}

class FNPropertyItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property Name")

class FNDeclaredStateItem(bpy.types.PropertyGroup):
    datablock_uuid: bpy.props.StringProperty()
    state_data_json: bpy.props.StringProperty()

class FNOverrideItem(bpy.types.PropertyGroup):
    datablock_uuid: bpy.props.StringProperty()
    override_data_json: bpy.props.StringProperty()

class FNInitialStateItem(bpy.types.PropertyGroup):
    """Stores a JSON snapshot of a datablock's state when it was first materialized."""
    datablock_uuid: bpy.props.StringProperty()
    state_data_json: bpy.props.StringProperty()

_classes_to_register = (
    FNPropertyItem,
    FNDeclaredStateItem,
    FNOverrideItem,
    FNInitialStateItem,
)

def register():
    for cls in _classes_to_register:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(_classes_to_register):
        bpy.utils.unregister_class(cls)
    # Clear the map on unregister to be clean
    _datablock_creation_map.clear()
