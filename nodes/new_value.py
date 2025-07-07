import bpy
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketBool, FNSocketFloat, FNSocketInt, FNSocketString, FNSocketVector, FNSocketColor
)
from .. import uuid_manager

_value_socket_map = {
    'BOOLEAN': 'FNSocketBool',
    'FLOAT': 'FNSocketFloat',
    'INTEGER': 'FNSocketInt',
    'STRING': 'FNSocketString',
    'VECTOR': 'FNSocketVector',
    'COLOR': 'FNSocketColor',
}

class FN_new_value(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_value"
    bl_label = "New Value"

    value_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('BOOLEAN', 'Boolean', ''),
            ('FLOAT', 'Float', ''),
            ('INTEGER', 'Integer', ''),
            ('STRING', 'String', ''),
            ('VECTOR', 'Vector', ''),
            ('COLOR', 'Color', ''),
        ],
        default='STRING',
        update=lambda self, context: self.update_sockets(context)
    )

    # Properties for different value types
    bool_value: bpy.props.BoolProperty(name="Value", default=False)
    float_value: bpy.props.FloatProperty(name="Value", default=0.0)
    int_value: bpy.props.IntProperty(name="Value", default=0)
    string_value: bpy.props.StringProperty(name="Value", default="")
    vector_value: bpy.props.FloatVectorProperty(name="Value", size=3, default=(0.0, 0.0, 0.0))
    color_value: bpy.props.FloatVectorProperty(name="Value", size=4, subtype='COLOR', default=(1.0, 1.0, 1.0, 1.0))

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear existing output sockets
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add new output socket based on selected type
        socket_type = _value_socket_map.get(self.value_type)
        if socket_type:
            self.outputs.new(socket_type, "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value_type", text="Type")
        
        # Draw the appropriate value property based on selected type
        if self.value_type == 'BOOLEAN':
            layout.prop(self, "bool_value")
        elif self.value_type == 'FLOAT':
            layout.prop(self, "float_value")
        elif self.value_type == 'INTEGER':
            layout.prop(self, "int_value")
        elif self.value_type == 'STRING':
            layout.prop(self, "string_value")
        elif self.value_type == 'VECTOR':
            layout.prop(self, "vector_value")
        elif self.value_type == 'COLOR':
            layout.prop(self, "color_value")

    def execute(self, **kwargs):
        # Return the appropriate value based on selected type
        if self.value_type == 'BOOLEAN':
            return self.bool_value
        elif self.value_type == 'FLOAT':
            return self.float_value
        elif self.value_type == 'INTEGER':
            return self.int_value
        elif self.value_type == 'STRING':
            return self.string_value
        elif self.value_type == 'VECTOR':
            return self.vector_value
        elif self.value_type == 'COLOR':
            return self.color_value
        return None
