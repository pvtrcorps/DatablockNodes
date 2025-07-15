
import bpy
import json
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketBool, FNSocketFloat, FNSocketInt, FNSocketString, FNSocketVector, FNSocketColor,
    FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld, FNSocketArmature, FNSocketAction
)
from ..properties import FNPropertyItem, _datablock_socket_map, FNRnaPropertyItem

# --- Mappings and Helpers ---

_rna_type_to_socket_map = {
    'BOOLEAN': 'FNSocketBool', 'INT': 'FNSocketInt', 'FLOAT': 'FNSocketFloat',
    'STRING': 'FNSocketString', 'ENUM': 'FNSocketString', 'FLOAT_VECTOR': 'FNSocketVector',
    'COLOR': 'FNSocketColor',
    'POINTER': {
        'Object': 'FNSocketObject', 'Scene': 'FNSocketScene', 'Collection': 'FNSocketCollection',
        'Material': 'FNSocketMaterial', 'Mesh': 'FNSocketMesh', 'Light': 'FNSocketLight',
        'Camera': 'FNSocketCamera', 'Image': 'FNSocketImage', 'NodeTree': 'FNSocketNodeTree',
        'Text': 'FNSocketText', 'World': 'FNSocketWorld', 'WorkSpace': 'FNSocketWorkSpace',
        'Armature': 'FNSocketArmature', 'Action': 'FNSocketAction',
    }
}

_datablock_socket_types = set(_rna_type_to_socket_map['POINTER'].values())

def get_socket_type_for_rna_property(rna_prop):
    if not rna_prop or not hasattr(rna_prop, 'type'): return None
    if rna_prop.type == 'POINTER':
        if hasattr(rna_prop, 'fixed_type') and rna_prop.fixed_type:
            return _rna_type_to_socket_map['POINTER'].get(rna_prop.fixed_type.bl_rna.identifier)
    else:
        return _rna_type_to_socket_map.get(rna_prop.type)
    return None

def build_rna_properties_recursive(node, rna_struct, path_prefix="", ui_path_prefix="", collection=None, visited_structs=None):
    if visited_structs is None: visited_structs = set()
    if not rna_struct or not hasattr(rna_struct, 'properties') or rna_struct.identifier in visited_structs:
        return
    visited_structs.add(rna_struct.identifier)

    for prop in rna_struct.properties:
        current_rna_path = f"{path_prefix}{prop.identifier}"
        current_ui_path = f"{ui_path_prefix}{prop.name}"

        # --- 1. Recursion Logic ---
        # We recurse into ANY pointer that points to another structure, even if the pointer itself is read-only.
        if prop.type == 'POINTER' and hasattr(prop, 'fixed_type') and prop.fixed_type:
            is_major_datablock = False
            socket_type = _rna_type_to_socket_map['POINTER'].get(prop.fixed_type.bl_rna.identifier)
            if socket_type in _datablock_socket_types:
                is_major_datablock = True

            if not node.show_datablock_pointers and is_major_datablock:
                continue
            
            sub_rna_struct = prop.fixed_type.bl_rna
            if hasattr(sub_rna_struct, 'properties'):
                build_rna_properties_recursive(
                    node, 
                    sub_rna_struct, 
                    path_prefix=f"{current_rna_path}.", 
                    ui_path_prefix=f"{current_ui_path} > ", 
                    collection=collection, 
                    visited_structs=visited_structs.copy()
                )

        # --- 2. Add Socket Logic ---
        # We only add a socket for the property if it's writable and has a corresponding socket type.
        if prop.is_readonly or prop.identifier == "rna_type":
            continue

        socket_type_for_add = get_socket_type_for_rna_property(prop)
        if socket_type_for_add:
            item = collection.add()
            item.name = current_ui_path
            item.rna_path = current_rna_path
            item.description = prop.description

def get_rna_property_from_path(base_rna_struct, rna_path):
    current_struct = base_rna_struct
    path_parts = rna_path.split('.')
    for i, part in enumerate(path_parts):
        if not hasattr(current_struct, 'properties'): return None
        prop = current_struct.properties.get(part)
        if prop is None: return None
        if i == len(path_parts) - 1:
            return prop
        else:
            if hasattr(prop, 'fixed_type') and prop.fixed_type:
                current_struct = prop.fixed_type.bl_rna
            else:
                return None
    return None

def _update_node(self, context):
    self._update_available_properties()
    bpy.app.timers.register(lambda: self.update_sockets(context), first_interval=0.01)
    self.id_data.update_tag()

# --- Node Definition ---

class FN_set_datablock_properties(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_datablock_properties"
    bl_label = "Set Datablock Properties"

    datablock_type: bpy.props.EnumProperty(
        name="Datablock Type",
        items=[
            ('OBJECT', 'Object', ''), ('SCENE', 'Scene', ''), ('COLLECTION', 'Collection', ''),
            ('MATERIAL', 'Material', ''), ('MESH', 'Mesh', ''), ('LIGHT', 'Light', ''),
            ('CAMERA', 'Camera', ''), ('IMAGE', 'Image', ''), ('NODETREE', 'Node Tree', ''),
            ('TEXT', 'Text', ''), ('WORLD', 'World', ''), ('WORKSPACE', 'WorkSpace', ''),
            ('ARMATURE', 'Armature', ''), ('ACTION', 'Action', ''),
        ],
        default='OBJECT',
        update=_update_node
    )

    show_datablock_pointers: bpy.props.BoolProperty(
        name="Show Datablock Pointers",
        description="Include properties that point to other main datablocks (e.g., objects, materials)",
        default=True,
        update=_update_node
    )

    rna_path_selector: bpy.props.StringProperty(name="RNA Property Path")
    properties_to_set: bpy.props.CollectionProperty(type=FNPropertyItem)
    available_rna_properties: bpy.props.CollectionProperty(type=FNRnaPropertyItem)

    def _update_available_properties(self):
        self.available_rna_properties.clear()
        rna_type = getattr(bpy.types, self.datablock_type.title().replace("_", ""), None) or getattr(bpy.types, self.datablock_type.capitalize(), None)
        if rna_type:
            build_rna_properties_recursive(self, rna_type.bl_rna, collection=self.available_rna_properties)

    def init(self, context):
        FNBaseNode.init(self, context)
        self._update_available_properties()
        self.update_sockets(context)

    def update_sockets(self, context):
        links_to_restore = []
        for socket in self.inputs:
            if socket.name != "Target":
                for link in socket.links:
                    links_to_restore.append((link.from_socket, socket.name))

        for socket in list(self.inputs):
            if socket.name != "Target": self.inputs.remove(socket)
        
        main_socket_type = _datablock_socket_map.get(self.datablock_type, 'FNSocketObject')
        if "Target" not in self.inputs or self.inputs["Target"].bl_idname != main_socket_type:
            if "Target" in self.inputs: self.inputs.remove(self.inputs["Target"])
            if "Target" in self.outputs: self.outputs.remove(self.outputs["Target"])
            main_input = self.inputs.new(main_socket_type, "Target")
            main_input.is_mutable = True
            self.outputs.new(main_socket_type, "Target")

        rna_type = getattr(bpy.types, self.datablock_type.title().replace("_", ""), None) or getattr(bpy.types, self.datablock_type.capitalize(), None)
        if not rna_type: return

        for prop_item in self.properties_to_set:
            rna_property = get_rna_property_from_path(rna_type.bl_rna, prop_item.rna_path)
            if rna_property:
                socket_bl_idname = get_socket_type_for_rna_property(rna_property)
                if socket_bl_idname:
                    self.inputs.new(socket_bl_idname, prop_item.name)

        for from_socket, to_socket_name in links_to_restore:
            if to_socket_name in self.inputs:
                self.id_data.links.new(from_socket, self.inputs[to_socket_name])

    def draw_buttons(self, context, layout):
        col = layout.column(align=True)
        col.prop(self, "datablock_type", text="")
        row = col.row(align=True)
        row.prop_search(self, "rna_path_selector", self, "available_rna_properties", text="")
        
        actual_rna_path = ""
        if self.rna_path_selector:
            prop_item = next((p for p in self.available_rna_properties if p.name == self.rna_path_selector), None)
            if prop_item: actual_rna_path = prop_item.rna_path

        is_already_set = any(p.rna_path == actual_rna_path for p in self.properties_to_set) if actual_rna_path else False
        op_icon = 'REMOVE' if is_already_set else 'ADD'
        op_action = 'REMOVE' if is_already_set else 'ADD'

        add_remove_op = row.operator("fn.internal_add_remove_property", text="", icon=op_icon, emboss=False)
        add_remove_op.node_path = self.path_from_id()
        add_remove_op.rna_path = actual_rna_path
        add_remove_op.action = op_action

        if is_already_set and actual_rna_path:
            reorder_up_op = row.operator("fn.internal_reorder_property", text="", icon='TRIA_UP', emboss=False)
            reorder_up_op.node_path = self.path_from_id()
            reorder_up_op.rna_path = actual_rna_path
            reorder_up_op.direction = 'UP'

            reorder_down_op = row.operator("fn.internal_reorder_property", text="", icon='TRIA_DOWN', emboss=False)
            reorder_down_op.node_path = self.path_from_id()
            reorder_down_op.rna_path = actual_rna_path
            reorder_down_op.direction = 'DOWN'
        
        col.prop(self, "show_datablock_pointers")

    def execute(self, **kwargs):
        target_uuid = kwargs.get(self.inputs["Target"].identifier)
        if not target_uuid: return {self.outputs[0].identifier: None}

        assignments = []
        for prop_item in self.properties_to_set:
            socket = self.inputs.get(prop_item.name)
            if not socket: continue
            prop_value = kwargs.get(socket.identifier)
            if prop_value is None: continue

            if socket.bl_idname in _datablock_socket_types:
                assignments.append({
                    'target_uuid': target_uuid, 'property_name': prop_item.rna_path,
                    'value_type': 'UUID', 'value_uuid': prop_value, 'value_json': ''
                })
            else:
                assignments.append({
                    'target_uuid': target_uuid, 'property_name': prop_item.rna_path,
                    'value_type': 'LITERAL', 'value_uuid': '', 'value_json': json.dumps(prop_value)
                })

        return {self.outputs[0].identifier: target_uuid, 'property_assignments': assignments}

# --- Internal Operators ---

class FN_OT_internal_add_remove_property(bpy.types.Operator):
    bl_idname = "fn.internal_add_remove_property"
    bl_label = "Add/Remove Property for Node"
    bl_options = {'REGISTER', 'UNDO'}

    node_path: bpy.props.StringProperty()
    rna_path: bpy.props.StringProperty()
    action: bpy.props.EnumProperty(items=[('ADD', 'Add', ''), ('REMOVE', 'Remove', '')])

    def execute(self, context):
        node = context.space_data.edit_tree.path_resolve(self.node_path)
        if not node or not self.rna_path: return {'CANCELLED'}

        if self.action == 'ADD':
            if not any(p.rna_path == self.rna_path for p in node.properties_to_set):
                selected_prop = next((p for p in node.available_rna_properties if p.rna_path == self.rna_path), None)
                if selected_prop:
                    prop_item = node.properties_to_set.add()
                    prop_item.rna_path = selected_prop.rna_path
                    prop_item.name = selected_prop.name
        elif self.action == 'REMOVE':
            for i, prop_item in enumerate(node.properties_to_set):
                if prop_item.rna_path == self.rna_path:
                    node.properties_to_set.remove(i)
                    break
        
        node.update_sockets(context)
        node.id_data.update_tag()
        return {'FINISHED'}

class FN_OT_internal_reorder_property(bpy.types.Operator):
    bl_idname = "fn.internal_reorder_property"
    bl_label = "Reorder Property for Node"
    bl_options = {'REGISTER', 'UNDO'}

    node_path: bpy.props.StringProperty()
    rna_path: bpy.props.StringProperty()
    direction: bpy.props.EnumProperty(items=[('UP', 'Up', ''), ('DOWN', 'Down', '')])

    def execute(self, context):
        node = context.space_data.edit_tree.path_resolve(self.node_path)
        if not node or not self.rna_path: return {'CANCELLED'}

        prop_idx = next((i for i, p in enumerate(node.properties_to_set) if p.rna_path == self.rna_path), -1)
        if prop_idx == -1: return {'CANCELLED'}

        if self.direction == 'UP' and prop_idx > 0:
            node.properties_to_set.move(prop_idx, prop_idx - 1)
        elif self.direction == 'DOWN' and prop_idx < len(node.properties_to_set) - 1:
            node.properties_to_set.move(prop_idx, prop_idx + 1)

        node.update_sockets(context)
        node.id_data.update_tag()
        return {'FINISHED'}

def register():
    bpy.utils.register_class(FN_set_datablock_properties)
    bpy.utils.register_class(FN_OT_internal_add_remove_property)
    bpy.utils.register_class(FN_OT_internal_reorder_property)

def unregister():
    bpy.utils.unregister_class(FN_set_datablock_properties)
    bpy.utils.unregister_class(FN_OT_internal_add_remove_property)
    bpy.utils.unregister_class(FN_OT_internal_reorder_property)
