
import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import (
    FNSocketString, FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld
)

_datablock_socket_map = {
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
}

class FN_set_datablock_name(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_datablock_name"
    bl_label = "Set Datablock Name"

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
        ],
        default='SCENE',
        update=lambda self, context: self.update_sockets(context)
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear all existing sockets except 'Name' input
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add datablock input socket
        datablock_socket = self.inputs.new(_datablock_socket_map[self.datablock_type], self.datablock_type.capitalize())
        datablock_socket.is_mutable = True

        # Add new name input socket
        self.inputs.new('FNSocketString', "New Name")

        # Add datablock output socket
        self.outputs.new(_datablock_socket_map[self.datablock_type], self.datablock_type.capitalize())

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")

    def execute(self, **kwargs):
        input_socket_name = self.datablock_type.capitalize()
        input_datablock = kwargs.get(self.inputs[input_socket_name].identifier)
        new_name = kwargs.get(self.inputs['New Name'].identifier)

        if not input_datablock:
            print(f"  - Warning: No input datablock provided to {self.name}. Skipping.")
            return None

        if new_name is None:
            print(f"  - Warning: No new name provided to {self.name}. Skipping.")
            return input_datablock # Return datablock unmodified

        input_datablock.name = new_name
        return {self.outputs[0].identifier: input_datablock}
