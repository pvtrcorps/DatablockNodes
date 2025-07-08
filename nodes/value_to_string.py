import bpy
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketBool, FNSocketFloat, FNSocketInt, FNSocketVector, FNSocketColor,
    FNSocketString
)

class FN_value_to_string(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_value_to_string"
    bl_label = "Value to String"

    value_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('BOOLEAN', 'Boolean', ''),
            ('FLOAT', 'Float', ''),
            ('INTEGER', 'Integer', ''),
            ('VECTOR', 'Vector', ''),
            ('COLOR', 'Color', ''),
        ],
        default='BOOLEAN',
        update=lambda self, context: self.update_sockets(context)
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.manages_scene_datablock = False
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear existing sockets
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add input socket based on selected value_type
        _socket_map = {
            'BOOLEAN': 'FNSocketBool',
            'FLOAT': 'FNSocketFloat',
            'INTEGER': 'FNSocketInt',
            'VECTOR': 'FNSocketVector',
            'COLOR': 'FNSocketColor',
        }
        self.inputs.new(_socket_map[self.value_type], "Value")

        # Add output string socket
        self.outputs.new('FNSocketString', "String")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value_type", text="Type")

    def execute(self, **kwargs):
        input_value = kwargs.get(self.inputs['Value'].identifier)

        if input_value is None:
            return {self.outputs['String'].identifier: ""}

        return {self.outputs['String'].identifier: str(input_value)}
