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

_socket_single = {
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
    # 'VIEW_LAYER': 'FNSocketViewLayer', # Not yet implemented
}

class FN_switch(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_switch"
    bl_label = "Switch"

    data_type: bpy.props.EnumProperty(
        name="Type",
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
        update=lambda self, context: self.update_type(context)
    )

    def update_type(self, context):
        self._update_sockets()

    def _update_sockets(self):
        # Clear existing sockets
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add Switch input (boolean)
        self.inputs.new('FNSocketBool', "Switch")

        # Add False and True inputs based on selected data_type
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
            false_socket = self.inputs.new(socket_type, "False")
            false_socket.is_mutable = False
            if self.data_type.endswith('_LIST'):
                false_socket.display_shape = 'SQUARE'
            true_socket = self.inputs.new(socket_type, "True")
            true_socket.is_mutable = False
            if self.data_type.endswith('_LIST'):
                true_socket.display_shape = 'SQUARE'

            # Add output socket
            new_output_socket = self.outputs.new(socket_type, "Output")
            if self.data_type.endswith('_LIST'):
                new_output_socket.display_shape = 'SQUARE'

    def init(self, context):
        FNBaseNode.init(self, context)
        self._update_sockets()

    def draw_buttons(self, context, layout):
        layout.prop(self, "data_type", text="Type")

    def execute(self, **kwargs):
        switch_value = kwargs.get(self.inputs['Switch'].identifier)
        false_value = kwargs.get(self.inputs['False'].identifier)
        true_value = kwargs.get(self.inputs['True'].identifier)

        output_value = true_value if switch_value else false_value

        return output_value
