import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString

class FN_join_strings(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_join_strings"
    bl_label = "Join Strings"

    string_count: bpy.props.IntProperty(
        name="Strings",
        default=2,
        min=0,
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

        # Add separator input
        self.inputs.new('FNSocketString', "Separator")

        # Add string input sockets
        for i in range(self.string_count):
            self.inputs.new('FNSocketString', str(i))

        # Add output string socket
        self.outputs.new('FNSocketString', "Output")

    def draw_buttons(self, context, layout):
        layout.prop(self, "string_count", text="Strings")

    def execute(self, **kwargs):
        separator = kwargs.get(self.inputs['Separator'].identifier, "")
        
        joined_string = []
        for i in range(self.string_count):
            input_string = kwargs.get(self.inputs[str(i)].identifier)
            if input_string is not None:
                joined_string.append(str(input_string))
        
        return {self.outputs['Output'].identifier: separator.join(joined_string)}
