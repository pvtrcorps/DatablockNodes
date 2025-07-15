import bpy
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketBool, FNSocketFloat, FNSocketInt, FNSocketString, FNSocketVector, FNSocketColor
)

_value_socket_map = {
    'BOOLEAN': 'FNSocketBool',
    'FLOAT': 'FNSocketFloat',
    'INTEGER': 'FNSocketInt',
    'STRING': 'FNSocketString',
    'VECTOR': 'FNSocketVector',
    'COLOR': 'FNSocketColor',
}

def _update_node(self, context):
    self.update_sockets(context)

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
        update=_update_node
    )

    # Properties for different value types
    bool_value: bpy.props.BoolProperty(name="Value", default=False, update=FNBaseNode._trigger_update)
    float_value: bpy.props.FloatProperty(name="Value", default=0.0, update=FNBaseNode._trigger_update)
    int_value: bpy.props.IntProperty(name="Value", default=0, update=FNBaseNode._trigger_update)
    string_value: bpy.props.StringProperty(name="Value", default="", update=FNBaseNode._trigger_update)
    vector_value: bpy.props.FloatVectorProperty(name="Value", size=3, default=(0.0, 0.0, 0.0), update=FNBaseNode._trigger_update)
    color_value: bpy.props.FloatVectorProperty(name="Value", size=4, subtype='COLOR', default=(1.0, 1.0, 1.0, 1.0), update=FNBaseNode._trigger_update)

    def init(self, context):
        FNBaseNode.init(self, context)
        self.manages_scene_datablock = False
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
        output_value = None
        if self.value_type == 'BOOLEAN':
            output_value = self.bool_value if hasattr(self, 'bool_value') else False
        elif self.value_type == 'FLOAT':
            output_value = self.float_value if hasattr(self, 'float_value') else 0.0
        elif self.value_type == 'INTEGER':
            output_value = self.int_value if hasattr(self, 'int_value') else 0
        elif self.value_type == 'STRING':
            output_value = self.string_value if hasattr(self, 'string_value') else ""
        elif self.value_type == 'VECTOR':
            output_value = self.vector_value if hasattr(self, 'vector_value') else (0.0, 0.0, 0.0)
        elif self.value_type == 'COLOR':
            output_value = self.color_value if hasattr(self, 'color_value') else (1.0, 1.0, 1.0, 1.0)
        
        # Fallback for cases where value_type might not match any property (e.g., after type change)
        if output_value is None:
            if self.value_type == 'BOOLEAN': output_value = False
            elif self.value_type == 'FLOAT': output_value = 0.0
            elif self.value_type == 'INTEGER': output_value = 0
            elif self.value_type == 'STRING': output_value = ""
            elif self.value_type == 'VECTOR': output_value = (0.0, 0.0, 0.0)
            elif self.value_type == 'COLOR': output_value = (1.0, 1.0, 1.0, 1.0)
            else: output_value = "" # Generic fallback
        
        return {self.outputs['Value'].identifier: output_value}