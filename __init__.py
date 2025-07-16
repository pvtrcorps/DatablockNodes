
bl_info = {
    "name": "Datablock Nodes",
    "author": "Your Name Here",
    "version": (2, 0, 0),
    "blender": (3, 0, 0),
    "location": "Node Editor",
    "description": "A declarative, procedural datablock management system.",
    "warning": "",
    "doc_url": "",
    "category": "Node",
}


from . import logger
logger.log("--- Loading Datablock Nodes Addon ---")

import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

from . import operators
from . import sockets
from . import properties
from . import reconciler
from .nodes import new_datablock, set_datablock_name, link_to_scene, create_list, new_value, link_to_collection, join_strings, split_string, value_to_string, switch, get_item_from_list, import_datablock, read_file, write_file, set_datablock_properties, set_object_data, set_scene_world, set_object_material, set_object_parent, derive_datablock, get_datablock_content, sequence_of_actions
from .nodes.set_datablock_properties import FN_OT_internal_add_remove_property, FN_OT_internal_reorder_property

# --- State Map Item ---
class FNStateMapItem(bpy.types.PropertyGroup):
    node_id: bpy.props.StringProperty()
    socket_identifier: bpy.props.StringProperty() # New: Identifier of the socket this item belongs to
    datablock_uuids: bpy.props.StringProperty()

# --- Property Assignment Map Item ---
class FNPropertyAssignmentItem(bpy.types.PropertyGroup):
    target_uuid: bpy.props.StringProperty()
    property_name: bpy.props.StringProperty()
    value_type: bpy.props.EnumProperty(
        items=[('UUID', 'UUID', ''), ('LITERAL', 'Literal', '')],
        default='UUID'
    )
    value_uuid: bpy.props.StringProperty() # For UUID-based assignments
    value_json: bpy.props.StringProperty() # For literal value assignments (JSON encoded)

# --- Relationship Map Item ---
class FNRelationshipItem(bpy.types.PropertyGroup):
    node_id: bpy.props.StringProperty()
    source_uuid: bpy.props.StringProperty()
    target_uuid: bpy.props.StringProperty()
    relationship_type: bpy.props.StringProperty() # e.g., "COLLECTION_OBJECT_LINK", "COLLECTION_CHILD_LINK"


# --- Node Tree ---
class DatablockTree(bpy.types.NodeTree):
    """A node tree for procedural datablock management."""
    bl_idname = 'DatablockTreeType'
    bl_label = "Datablock Node Tree"
    bl_icon = 'NODETREE'

    # Property to store the state map
    fn_state_map: bpy.props.CollectionProperty(type=FNStateMapItem)
    # Property to store the property assignments map
    fn_property_assignments_map: bpy.props.CollectionProperty(type=FNPropertyAssignmentItem)
    # Property to store the relationships map
    fn_relationships_map: bpy.props.CollectionProperty(type=FNRelationshipItem)
    # Property to store the overrides map
    fn_override_map: bpy.props.CollectionProperty(type=properties.FNOverrideItem)

# --- UI ---
class DATABLOCK_PT_panel(bpy.types.Panel):
    bl_label = "Datablock Nodes"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Datablock"

    @classmethod
    def poll(cls, context):
        if context.space_data and hasattr(context.space_data, 'tree_type'):
            return context.space_data.tree_type == 'DatablockTreeType'
        return False

    def draw(self, context):
        layout = self.layout
        

# --- Node Categories ---
node_categories = [
    NodeCategory("DATABLOCK_NODES", "Nodes", items=[
        NodeItem("FN_new_datablock"),
        NodeItem("FN_import_datablock"),
        NodeItem("FN_derive_datablock"),
        NodeItem("FN_get_datablock_content"),
        NodeItem("FN_new_value"),
        NodeItem("FN_set_datablock_name"),
        NodeItem("FN_link_to_scene"),
        NodeItem("FN_link_to_collection"),
        NodeItem("FN_create_list"),
        NodeItem("FN_switch"),
        NodeItem("FN_join_strings"),
        NodeItem("FN_split_string"),
        NodeItem("FN_value_to_string"),
        NodeItem("FN_get_item_from_list"),
        NodeItem("FN_read_file"),
        NodeItem("FN_write_file"),
        NodeItem("FN_set_datablock_properties"),
        NodeItem("FN_set_object_data"),
        NodeItem("FN_set_scene_world"),
        NodeItem("FN_set_object_material"),
        NodeItem("FN_set_object_parent"),
        NodeItem("FN_sequence_of_actions"),
    ]),
]

# --- REGISTRATION ---

classes = (
    FNStateMapItem,
    FNPropertyAssignmentItem,
    FNRelationshipItem,
    DatablockTree,
    
    DATABLOCK_PT_panel,
    new_datablock.FN_new_datablock,
    import_datablock.FN_import_datablock,
    derive_datablock.FN_derive_datablock,
    get_datablock_content.FN_get_datablock_content,
    new_value.FN_new_value,
    set_datablock_name.FN_set_datablock_name,
    link_to_scene.FN_link_to_scene,
    link_to_collection.FN_link_to_collection,
    create_list.FN_create_list,
    switch.FN_switch,
    join_strings.FN_join_strings,
    split_string.FN_split_string,
    value_to_string.FN_value_to_string,
    get_item_from_list.FN_get_item_from_list,
    read_file.FN_read_file,
    write_file.FN_write_file,
    set_datablock_properties.FN_set_datablock_properties,
    set_object_data.FN_set_object_data,
    set_scene_world.FN_set_scene_world,
    set_object_material.FN_set_object_material,
    set_object_parent.FN_set_object_parent,
    sequence_of_actions.FN_sequence_of_actions,
    FN_OT_internal_add_remove_property,
    FN_OT_internal_reorder_property,
)

def register():
    logger.log("[FN_Register] Registering addon...")
    operators.register()
    sockets.register()
    properties.register() # New registration
    for cls in classes:
        bpy.utils.register_class(cls)
    
    register_node_categories("DATABLOCK_NODES", node_categories)

    # Register the main depsgraph update handler for continuous execution
    bpy.app.handlers.depsgraph_update_post.append(reconciler.datablock_nodes_depsgraph_handler)

def unregister():
    logger.log("[FN_Register] Unregistering addon...")
    unregister_node_categories("DATABLOCK_NODES")

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    sockets.unregister()
    properties.unregister() # New unregistration
    operators.unregister()

    # Remove the handler
    try:
        bpy.app.handlers.depsgraph_update_post.remove(reconciler.datablock_nodes_depsgraph_handler)
        logger.log("[FN_Register] App handler removed.")
    except ValueError:
        logger.log("[FN_Register] App handler was not found, could not remove.")

if __name__ == "__main__":
    register()

