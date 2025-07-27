bl_info = {
    "name": "Datablock Nodes",
    "author": "Gemini & The V5.3 Architecture Team",
    "version": (5, 3, 0),
    "blender": (3, 0, 0),
    "location": "Node Editor",
    "description": "A hierarchical, non-destructive scene composition engine.",
    "warning": "",
    "doc_url": "",
    "category": "Node",
}

from . import logger
logger.log("--- Loading Datablock Nodes Addon (V5.3 Engine) ---")

import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories

# --- Core Modules ---
from . import properties
from . import sockets
from . import operators
from . import override_handler # The override handler is still a key feature
from .engine import entry_point

# --- V5.3 Node Imports ---
from .nodes import (
    create_primitive,
    import_node,
    scene,
    collection,
    select,
    union_selection,
    intersection_selection,
    difference_selection,
    merge,
    set_property,
    prune,
    parent,
    set_collection,
    parent_collection,
    create_scene_list,
    batch_render,
    string,
    join_strings,
)

# --- Node Tree ---
class DatablockTree(bpy.types.NodeTree):
    bl_idname = 'DatablockTreeType'
    bl_label = "Datablock Node Tree"
    bl_icon = 'NODETREE'
    fn_declared_state_map: bpy.props.CollectionProperty(type=properties.FNDeclaredStateItem)
    fn_override_map: bpy.props.CollectionProperty(type=properties.FNOverrideItem)
    fn_initial_state_map: bpy.props.CollectionProperty(type=properties.FNInitialStateItem)

# --- UI ---
class DATABLOCK_PT_panel(bpy.types.Panel):
    bl_label = "Datablock Nodes"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Datablock"
    @classmethod
    def poll(cls, context):
        return context.space_data and hasattr(context.space_data, 'tree_type') and context.space_data.tree_type == 'DatablockTreeType'
    def draw(self, context):
        pass

# --- V5.3 Node Categories ---
node_categories = [
    NodeCategory("INPUT", "Input", items=[
        NodeItem(scene.FN_scene.bl_idname),
        NodeItem(import_node.FN_import.bl_idname),
        NodeItem(create_primitive.FN_create_primitive.bl_idname),
        # NodeItem(reference.FN_reference.bl_idname), # Will be added later
    ]),
    NodeCategory("SELECTION", "Selection", items=[
        NodeItem(select.FN_select.bl_idname),
        NodeItem(union_selection.FN_union_selection.bl_idname),
        NodeItem(intersection_selection.FN_intersection_selection.bl_idname),
        NodeItem(difference_selection.FN_difference_selection.bl_idname),
    ]),
    NodeCategory("COMPOSITION", "Composition", items=[
        NodeItem(merge.FN_merge.bl_idname),
    ]),
    NodeCategory("MODIFIERS", "Modifiers", items=[
        NodeItem(set_property.FN_set_property.bl_idname),
        NodeItem(prune.FN_prune.bl_idname),
        NodeItem(parent.FN_parent.bl_idname),
        NodeItem(set_collection.FN_set_collection.bl_idname),
        NodeItem(parent_collection.FN_parent_collection.bl_idname),
    ]),
    NodeCategory("VALUES", "Values", items=[
        NodeItem(string.FN_string.bl_idname),
        NodeItem(join_strings.FN_join_strings.bl_idname),
    ]),
    NodeCategory("EXECUTORS", "Executors", items=[
        NodeItem(create_scene_list.FN_create_scene_list.bl_idname),
        NodeItem(batch_render.FN_batch_render.bl_idname),
    ]),
]

# --- Registration ---
# Gather all node classes and other classes to register
classes_to_register = (
    DatablockTree,
    DATABLOCK_PT_panel,
    # Input Nodes
    scene.FN_scene,
    import_node.FN_import,
    create_primitive.FN_create_primitive,
    # collection.FN_collection, # This is a generator, should be in Create Primitive
    
    # Selection Nodes
    select.FN_select,
    union_selection.FN_union_selection,
    intersection_selection.FN_intersection_selection,
    difference_selection.FN_difference_selection,
    
    # Composition Nodes
    merge.FN_merge,
    
    # Modifier Nodes
    set_property.FN_set_property,
    prune.FN_prune,
    parent.FN_parent,
    set_collection.FN_set_collection,
    parent_collection.FN_parent_collection,
    
    # Value Nodes
    string.FN_string,
    join_strings.FN_join_strings,

    # Executor Nodes
    create_scene_list.FN_create_scene_list,
) + batch_render._classes # batch_render includes an operator

def register():
    logger.log("[FN_Register] Registering V5.3 Engine...")
    
    properties.register()
    sockets.register()
    operators.register()
    
    for cls in classes_to_register:
        bpy.utils.register_class(cls)
        
    register_node_categories("DATABLOCK_NODES", node_categories)
    
    override_handler.register()
    if entry_point.depsgraph_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(entry_point.depsgraph_update_handler)

def unregister():
    logger.log("[FN_Register] Unregistering V5.3 Engine...")
    
    if entry_point.depsgraph_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(entry_point.depsgraph_update_handler)
    override_handler.unregister()
        
    unregister_node_categories("DATABLOCK_NODES")
    
    for cls in reversed(classes_to_register):
        bpy.utils.unregister_class(cls)
        
    operators.unregister()
    sockets.unregister()
    properties.unregister()