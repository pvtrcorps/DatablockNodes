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
from .. import uuid_manager

def _update_node(self, context):
    self.update_sockets(context)
    self._trigger_update(context)

class FN_switch(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_switch"
    bl_label = "Switch"

    switch_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('BOOLEAN', 'Boolean', 'Switch based on a boolean value'),
            ('INDEX', 'Index', 'Switch based on an integer index'),
        ],
        default='BOOLEAN',
        update=_update_node
    )

    data_type: bpy.props.EnumProperty(
        name="Data",
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
        default='SCENE',
        update=_update_node
    )

    item_count: bpy.props.IntProperty(
        name="Items",
        default=2,
        min=0,
        update=_update_node
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        # --- Update Button Visibility ---
        value_types = ['BOOLEAN', 'FLOAT', 'INTEGER', 'STRING', 'VECTOR', 'COLOR', 'STRING_LIST']
        self.manages_scene_datablock = self.data_type not in value_types

        # Clear existing sockets
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

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

        if self.switch_type == 'BOOLEAN':
            self.inputs.new('FNSocketBool', "Switch")
            if socket_type:
                false_socket = self.inputs.new(socket_type, "False")
                false_socket.is_mutable = False
                if self.data_type.endswith('_LIST'):
                    false_socket.display_shape = 'SQUARE'
                true_socket = self.inputs.new(socket_type, "True")
                true_socket.is_mutable = False
                if self.data_type.endswith('_LIST'):
                    true_socket.display_shape = 'SQUARE'

        elif self.switch_type == 'INDEX':
            self.inputs.new('FNSocketInt', "Index")
            if socket_type:
                for i in range(self.item_count):
                    item_socket = self.inputs.new(socket_type, str(i))
                    item_socket.is_mutable = False
                    if self.data_type.endswith('_LIST'):
                        item_socket.display_shape = 'SQUARE'

        # Add output socket
        if socket_type:
            new_output_socket = self.outputs.new(socket_type, "Output")
            if self.data_type.endswith('_LIST'):
                new_output_socket.display_shape = 'SQUARE'

    

    def draw_buttons(self, context, layout):
        layout.prop(self, "switch_type", text="Type")
        layout.prop(self, "data_type", text="Data")
        if self.switch_type == 'INDEX':
            layout.prop(self, "item_count", text="Items")

    def execute(self, **kwargs):
        # The reconciler now handles the conditional evaluation.
        # This node's execute function is now passive and simply passes through the value
        # that the reconciler has already determined from the active branch.
        # The value is passed in kwargs, keyed by the output socket's identifier.
        return {self.outputs[0].identifier: kwargs.get(self.outputs[0].identifier)}