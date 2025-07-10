import bpy
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketBool, FNSocketFloat, FNSocketInt, FNSocketString, FNSocketVector, FNSocketColor,
    FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld,
    FNSocketSceneList, FNSocketObjectList, FNSocketCollectionList, FNSocketWorldList,
    FNSocketCameraList, FNSocketImageList, FNSocketLightList, FNSocketMaterialList,
    FNSocketMeshList, FNSocketNodeTreeList, FNSocketTextList, FNSocketWorkSpaceList
)

class FN_create_list(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_create_list"
    bl_label = "Create List"

    datablock_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('SCENE', 'Scene', ''),
            ('OBJECT', 'Object', ''),
            ('COLLECTION', 'Collection', ''),
            ('CAMERA', 'Camera', ''),
            ('IMAGE', 'Image', ''),
            ('LIGHT', 'Light', ''),
            ('MATERIAL', 'Material', ''),
            ('MESH', 'Mesh', ''),
            ('NODETREE', 'Node Tree', ''),
            ('TEXT', 'Text', ''),
            ('WORKSPACE', 'WorkSpace', ''),
            ('WORLD', 'World', ''),
            ('STRING', 'String', ''),
        ],
        default='SCENE',
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
        # --- Update Button Visibility ---
        value_types = ['STRING']
        self.manages_scene_datablock = self.datablock_type not in value_types

        # Clear existing sockets
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add input sockets
        _socket_map = {
            'SCENE': 'FNSocketScene',
            'OBJECT': 'FNSocketObject',
            'COLLECTION': 'FNSocketCollection',
            'CAMERA': 'FNSocketCamera',
            'IMAGE': 'FNSocketImage',
            'LIGHT': 'FNSocketLight',
            'MATERIAL': 'FNSocketMaterial',
            'MESH': 'FNSocketMesh',
            'NODETREE': 'FNSocketNodeTree',
            'TEXT': 'FNSocketText',
            'WORKSPACE': 'FNSocketWorkSpace',
            'WORLD': 'FNSocketWorld',
            'STRING': 'FNSocketString',
        }
        
        for i in range(self.item_count): # Use item_count here
            new_input_socket = self.inputs.new(_socket_map[self.datablock_type], str(i))
            new_input_socket.is_mutable = False

        # Add output list socket
        _list_socket_map = {
            'SCENE': 'FNSocketSceneList',
            'OBJECT': 'FNSocketObjectList',
            'COLLECTION': 'FNSocketCollectionList',
            'CAMERA': 'FNSocketCameraList',
            'IMAGE': 'FNSocketImageList',
            'LIGHT': 'FNSocketLightList',
            'MATERIAL': 'FNSocketMaterialList',
            'MESH': 'FNSocketMeshList',
            'NODETREE': 'FNSocketNodeTreeList',
            'TEXT': 'FNSocketTextList',
            'WORKSPACE': 'FNSocketWorkSpaceList',
            'WORLD': 'FNSocketWorldList',
            'STRING': 'FNSocketStringList',
        }
        list_socket_type = _list_socket_map.get(self.datablock_type)
        if list_socket_type:
            new_output_socket = self.outputs.new(list_socket_type, "List")
            new_output_socket.display_shape = 'SQUARE'

    def update_hash(self, hasher):
        super().update_hash(hasher)
        hasher.update(self.datablock_type.encode())
        hasher.update(str(self.item_count).encode())

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")
        layout.prop(self, "item_count", text="Items")

    def execute(self, **kwargs):
        list_of_items = []
        for input_socket in self.inputs:
            if input_socket.is_linked:
                # Get the value from the linked socket
                # The reconciler already puts the evaluated datablock/value into kwargs
                item_value = kwargs.get(input_socket.identifier)
                if item_value is not None:
                    list_of_items.append(item_value)
            elif hasattr(input_socket, 'default_value'):
                # If not linked, use the default value of the socket
                list_of_items.append(input_socket.default_value)
        
        return {self.outputs['List'].identifier: list_of_items}
