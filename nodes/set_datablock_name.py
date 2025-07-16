import bpy
import json
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import (
    FNSocketString, FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld
)
from .constants import DATABLOCK_TYPES, DATABLOCK_SOCKET_MAP

def _update_node(self, context):
    self.update_sockets(context)
    self._trigger_update(context)

class FN_set_datablock_name(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_datablock_name"
    bl_label = "Set Datablock Name"

    datablock_type: bpy.props.EnumProperty(
        name="Type",
        items=DATABLOCK_TYPES,
        default='SCENE',
        update=_update_node
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
        datablock_socket = self.inputs.new(DATABLOCK_SOCKET_MAP[self.datablock_type], self.datablock_type.capitalize())
        datablock_socket.is_mutable = True

        # Add new name input socket
        self.inputs.new('FNSocketString', "New Name")

        # Add datablock output socket
        self.outputs.new(DATABLOCK_SOCKET_MAP[self.datablock_type], self.datablock_type.capitalize())

    

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")

    def execute(self, **kwargs):
        input_socket_name = self.datablock_type.capitalize()
        input_datablock_uuid = kwargs.get(self.inputs[input_socket_name].identifier)
        new_name = kwargs.get(self.inputs['New Name'].identifier)
        assignments = []

        if input_datablock_uuid and new_name is not None:
            assignments.append({
                'target_uuid': input_datablock_uuid,
                'property_name': 'name',
                'value_type': 'LITERAL',
                'value_uuid': '',
                'value_json': json.dumps(new_name)
            })

        return {
            self.outputs[0].identifier: input_datablock_uuid,
            'property_assignments': assignments
        }