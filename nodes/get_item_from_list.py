import bpy
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketBool, FNSocketFloat, FNSocketInt, FNSocketString, FNSocketVector, FNSocketColor,
    FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld,
    FNSocketSceneList, FNSocketObjectList, FNSocketCollectionList, FNSocketWorldList,
    FNSocketCameraList, FNSocketImageList, FNSocketLightList, FNSocketMaterialList,
    FNSocketMeshList, FNSocketNodeTreeList, FNSocketTextList, FNSocketWorkSpaceList, FNSocketStringList
)

_socket_map_single = {
    'BOOLEAN': 'FNSocketBool',
    'FLOAT': 'FNSocketFloat',
    'INTEGER': 'FNSocketInt',
    'STRING': 'FNSocketString',
    'VECTOR': 'FNSocketVector',
    'COLOR': 'FNSocketColor',
    'SCENE': 'FNSocketScene',
    'OBJECT': 'FNSocketObject',
    'COLLECTION': 'FNSocketCollection',
    'WORLD': 'FNSocketWorld',
    'CAMERA': 'FNSocketCamera',
    'IMAGE': 'FNSocketImage',
    'LIGHT': 'FNSocketLight',
    'MATERIAL': 'FNSocketMaterial',
    'MESH': 'FNSocketMesh',
    'NODETREE': 'FNSocketNodeTree',
    'TEXT': 'FNSocketText',
    'WORKSPACE': 'FNSocketWorkSpace',
}

_socket_map_list = {
    'BOOLEAN': None, # No boolean list socket
    'FLOAT': None,   # No float list socket
    'INTEGER': None, # No integer list socket
    'STRING': 'FNSocketStringList',
    'VECTOR': None,  # No vector list socket
    'COLOR': None,   # No color list socket
    'SCENE': 'FNSocketSceneList',
    'OBJECT': 'FNSocketObjectList',
    'COLLECTION': 'FNSocketCollectionList',
    'WORLD': 'FNSocketWorldList',
    'CAMERA': 'FNSocketCameraList',
    'IMAGE': 'FNSocketImageList',
    'LIGHT': 'FNSocketLightList',
    'MATERIAL': 'FNSocketMaterialList',
    'MESH': 'FNSocketMeshList',
    'NODETREE': 'FNSocketNodeTreeList',
    'TEXT': 'FNSocketTextList',
    'WORKSPACE': 'FNSocketWorkSpaceList',
}

def _update_node(self, context):
    self.update_sockets(context)

class FN_get_item_from_list(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_get_item_from_list"
    bl_label = "Get Item From List"

    list_type: bpy.props.EnumProperty(
        name="List Type",
        items=[
            ('STRING', 'String', ''),
            ('SCENE', 'Scene', ''),
            ('OBJECT', 'Object', ''),
            ('COLLECTION', 'Collection', ''),
            ('WORLD', 'World', ''),
            ('CAMERA', 'Camera', ''),
            ('IMAGE', 'Image', ''),
            ('LIGHT', 'Light', ''),
            ('MATERIAL', 'Material', ''),
            ('MESH', 'Mesh', ''),
            ('NODETREE', 'Node Tree', ''),
            ('TEXT', 'Text', ''),
            ('WORKSPACE', 'WorkSpace', ''),
        ],
        default='OBJECT',
        update=_update_node
    )

    selection_mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('INDEX', 'By Index', 'Select item by its numerical index'),
            ('NAME', 'By Name', 'Select item by its name (only for datablocks)'),
        ],
        default='INDEX',
        update=_update_node
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        # --- Update Button Visibility ---
        self.manages_scene_datablock = self.list_type != 'STRING'

        # Clear existing sockets
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add list input socket
        list_socket_id = _socket_map_list.get(self.list_type)
        if list_socket_id:
            list_socket = self.inputs.new(list_socket_id, "List")
            list_socket.display_shape = 'SQUARE'
        else:
            print(f"Warning: No list socket defined for type {self.list_type}")
            return # Cannot proceed without a list input

        # Add selection mode input socket
        if self.selection_mode == 'INDEX':
            self.inputs.new('FNSocketInt', "Index")
        elif self.selection_mode == 'NAME':
            self.inputs.new('FNSocketString', "Name")

        # Add output item socket
        output_socket_id = _socket_map_single.get(self.list_type)
        if output_socket_id:
            self.outputs.new(output_socket_id, "Item")
        else:
            print(f"Warning: No single item socket defined for type {self.list_type}")

    

    def draw_buttons(self, context, layout):
        layout.prop(self, "list_type", text="List Type")
        layout.prop(self, "selection_mode", text="Mode")

    def execute(self, **kwargs):
        input_list = kwargs.get(self.inputs['List'].identifier)

        if not input_list or not isinstance(input_list, list):
            print(f"  - Warning: No valid list provided to {self.name}. Returning None.")
            return None

        if self.selection_mode == 'INDEX':
            index = kwargs.get(self.inputs['Index'].identifier)
            if index is None or not isinstance(index, int):
                print(f"  - Warning: Invalid index provided to {self.name}. Returning None.")
                return None
            
            if 0 <= index < len(input_list):
                return {self.outputs['Item'].identifier: input_list[index]}
            else:
                print(f"  - Warning: Index {index} out of bounds for {self.name} (0 to {len(input_list) - 1}). Returning None.")
                return {self.outputs['Item'].identifier: None}

        elif self.selection_mode == 'NAME':
            name_to_find = kwargs.get(self.inputs['Name'].identifier)
            if name_to_find is None or not isinstance(name_to_find, str):
                print(f"  - Warning: Invalid name provided to {self.name}. Returning None.")
                return {self.outputs['Item'].identifier: None}

            for item in input_list:
                if hasattr(item, 'name') and item.name == name_to_find:
                    return {self.outputs['Item'].identifier: item}
            print(f"  - Warning: Item with name '{name_to_find}' not found in the list. Returning None.")
            return {self.outputs['Item'].identifier: None}

        return {self.outputs['Item'].identifier: None}