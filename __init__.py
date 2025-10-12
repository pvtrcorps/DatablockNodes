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
import json
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories
from . import uuid_manager

# --- Core Modules ---
from . import properties
from . import sockets
from . import operators
from . import override_handler # The override handler is still a key feature
from .engine import entry_point

# --- V5.3 Node Imports ---
from .nodes import (
    create_object,
    import_node,
    scene,
    collection,
    outliner,
    merge,
    set_property,
    set_material,
    set_world,
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
        layout = self.layout
        tree = getattr(context.space_data, 'edit_tree', None)

        if not tree:
            return

        box = layout.box()
        row = box.row()
        row.label(text="User Overrides", icon='MODIFIER_DATA')
        
        override_count = 0
        if hasattr(tree, 'fn_override_map'):
            override_count = len(tree.fn_override_map)

        row.label(text=f"{override_count} active")
        op = row.operator("fn.clear_overrides", text="", icon='X')

        if override_count == 0:
            row.enabled = False
        else:
            box.separator()
            
            # Header
            header_row = box.row()
            header_row.label(text="Datablock")
            header_row.label(text="Overridden Properties")

            for override_item in tree.fn_override_map:
                item_row = box.row()
                db = uuid_manager.find_datablock_by_uuid(override_item.datablock_uuid)
                db_name = db.name if db else f"({override_item.datablock_uuid[:6]}...)"
                
                item_row.label(text=db_name)

                try:
                    overrides = json.loads(override_item.override_data_json)
                    props_str = ", ".join(overrides.keys())
                    item_row.label(text=props_str)
                except json.JSONDecodeError:
                    item_row.label(text="[Invalid Data]")

# --- V5.3 Node Categories ---
node_categories = [
    NodeCategory("INPUT", "Input", items=[
        NodeItem(scene.FN_scene.bl_idname),
        NodeItem(import_node.FN_import_node.bl_idname),
        NodeItem(create_object.FN_create_object.bl_idname),
        # NodeItem(reference.FN_reference.bl_idname), # Will be added later
    ]),
    
    NodeCategory("COMPOSITION", "Composition", items=[
        NodeItem(merge.FN_merge.bl_idname),
    ]),
    NodeCategory("MODIFIERS", "Modifiers", items=[
        NodeItem(set_property.FN_set_property.bl_idname),
        NodeItem(set_material.FN_set_material.bl_idname),
        NodeItem(set_world.FN_set_world.bl_idname),
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
    NodeCategory("DEBUG", "Debug", items=[
        NodeItem(outliner.FN_outliner.bl_idname),
    ]),
]

# --- Registration ---
# Gather all node classes and other classes to register
classes_to_register = (
    DatablockTree,
    DATABLOCK_PT_panel,
    outliner.OutlinerListItem,
    outliner.FN_UL_outliner_list,
    # Input Nodes
    scene.FN_scene,
    import_node.FN_import_node,
    create_object.FN_create_object,
    # collection.FN_collection, # This is a generator, should be in Create Primitive
    
    
    
    # Composition Nodes
    merge.FN_merge,
    
    # Modifier Nodes
    set_property.FN_set_property,
    set_material.FN_set_material,
    set_world.FN_set_world,
    prune.FN_prune,
    parent.FN_parent,
    set_collection.FN_set_collection,
    parent_collection.FN_parent_collection,
    
    # Value Nodes
    string.FN_string,
    join_strings.FN_join_strings,

    # Executor Nodes
    create_scene_list.FN_create_scene_list,
    outliner.FN_outliner,
    outliner.FN_OT_outliner_copy_path,
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