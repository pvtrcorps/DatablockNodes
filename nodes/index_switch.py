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

class FN_index_switch(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_index_switch"
    bl_label = "Index Switch"

    data_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('BOOLEAN', 'Boolean', ''),
            ('FLOAT', 'Float', ''),
            ('INTEGER', 'Integer', ''),
            ('STRING', 'String', ''),
            ('VECTOR', 'Vector', ''),
            ('COLOR', 'Color', ''),
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
            ('STRING_LIST', 'String List', ''),
            ('SCENE_LIST', 'Scene List', ''),
            ('OBJECT_LIST', 'Object List', ''),
            ('COLLECTION_LIST', 'Collection List', ''),
            ('WORLD_LIST', 'World List', ''),
            ('CAMERA_LIST', 'Camera List', ''),
            ('IMAGE_LIST', 'Image List', ''),
            ('LIGHT_LIST', 'Light List', ''),
            ('MATERIAL_LIST', 'Material List', ''),
            ('MESH_LIST', 'Mesh List', ''),
            ('NODETREE_LIST', 'Node Tree List', ''),
            ('TEXT_LIST', 'Text List', ''),
            ('WORKSPACE_LIST', 'WorkSpace List', ''),
        ],
        default='OBJECT',
        update=lambda self, context: self.update_sockets(context)
    )

    item_count: bpy.props.IntProperty(
        name="Items",
        default=2,
        min=0,
        update=lambda self, context: self.update_sockets(context)
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear existing sockets
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add Index input (integer)
        self.inputs.new('FNSocketInt', "Index")

        # Add dynamic item inputs based on selected data_type and item_count
        _socket_map = {
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
            'STRING_LIST': 'FNSocketStringList',
            'SCENE_LIST': 'FNSocketSceneList',
            'OBJECT_LIST': 'FNSocketObjectList',
            'COLLECTION_LIST': 'FNSocketCollectionList',
            'WORLD_LIST': 'FNSocketWorldList',
            'CAMERA_LIST': 'FNSocketCameraList',
            'IMAGE_LIST': 'FNSocketImageList',
            'LIGHT_LIST': 'FNSocketLightList',
            'MATERIAL_LIST': 'FNSocketMaterialList',
            'MESH_LIST': 'FNSocketMeshList',
            'NODETREE_LIST': 'FNSocketNodeTreeList',
            'TEXT_LIST': 'FNSocketTextList',
            'WORKSPACE_LIST': 'FNSocketWorkSpaceList',
        }
        socket_type = _socket_map.get(self.data_type)
        if socket_type:
            for i in range(self.item_count):
                item_socket = self.inputs.new(socket_type, f"Item {i}")
                item_socket.is_mutable = False
                if self.data_type.endswith('_LIST'):
                    item_socket.display_shape = 'SQUARE'

            # Add output socket
            new_output_socket = self.outputs.new(socket_type, "Output")
            if self.data_type.endswith('_LIST'):
                new_output_socket.display_shape = 'SQUARE'

    def draw_buttons(self, context, layout):
        layout.prop(self, "data_type", text="Type")
        layout.prop(self, "item_count", text="Items")

    def execute(self, **kwargs):
        index = kwargs.get(self.inputs['Index'].identifier)
        
        if index is None or not isinstance(index, int):
            print(f"  - Warning: Invalid index provided to {self.name}. Skipping.")
            return None

        # Collect all item values
        item_values = []
        for i in range(self.item_count):
            item_socket = self.inputs.get(f'Item {i}')
            if item_socket:
                item_values.append(kwargs.get(item_socket.identifier))
            else:
                item_values.append(None) # Should not happen if sockets are updated correctly

        if 0 <= index < len(item_values):
            return item_values[index]
        else:
            print(f"  - Warning: Index {index} out of bounds for {self.name} (0 to {len(item_values) - 1}). Returning None.")
            return None
