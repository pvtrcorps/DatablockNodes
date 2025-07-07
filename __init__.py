
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


import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

from . import operators
from . import sockets
from .nodes import new_datablock, set_datablock_name, link_to_scene, create_list, new_value, link_to_collection, join_strings, split_string, value_to_string, output_scenes, switch, execute, get_item_from_list

# --- State Map Item ---
class FNStateMapItem(bpy.types.PropertyGroup):
    node_id: bpy.props.StringProperty()
    datablock_uuid: bpy.props.StringProperty()

# --- Node Tree ---
class DatablockTree(bpy.types.NodeTree):
    """A node tree for procedural datablock management."""
    bl_idname = 'DatablockTreeType'
    bl_label = "Datablock Node Tree"
    bl_icon = 'NODETREE'

    # Property to store the state map
    fn_state_map: bpy.props.CollectionProperty(type=FNStateMapItem)

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
        NodeItem("FN_new_value"),
        NodeItem("FN_set_datablock_name"),
        NodeItem("FN_link_to_scene"),
        NodeItem("FN_link_to_collection"),
        NodeItem("FN_create_list"),
        NodeItem("FN_switch"),
        NodeItem("FN_join_strings"),
        NodeItem("FN_split_string"),
        NodeItem("FN_value_to_string"),
        NodeItem("FN_output_scenes"),
        NodeItem("FN_execute"),
        NodeItem("FN_get_item_from_list"),
    ]),
]

# --- REGISTRATION ---

classes = (
    FNStateMapItem,
    DatablockTree,
    
    DATABLOCK_PT_panel,
    new_datablock.FN_new_datablock,
    new_value.FN_new_value,
    set_datablock_name.FN_set_datablock_name,
    link_to_scene.FN_link_to_scene,
    link_to_collection.FN_link_to_collection,
    create_list.FN_create_list,
    switch.FN_switch,
    join_strings.FN_join_strings,
    split_string.FN_split_string,
    value_to_string.FN_value_to_string,
    output_scenes.FN_output_scenes,
    execute.FN_execute,
    get_item_from_list.FN_get_item_from_list,
)

def register():
    operators.register()
    sockets.register()
    for cls in classes:
        bpy.utils.register_class(cls)
    
    register_node_categories("DATABLOCK_NODES", node_categories)

def unregister():
    unregister_node_categories("DATABLOCK_NODES")

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    sockets.unregister()
    operators.unregister()

if __name__ == "__main__":
    register()

