import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString

class FN_join_strings(FNBaseNode, bpy.types.Node):
    """Joins multiple strings together."""
    bl_idname = "FN_join_strings"
    bl_label = "Join Strings"

    separator: bpy.props.StringProperty(
        name="Separator", 
        default=", ",
        update=lambda s,c: s.id_data.update_tag()
    )

    string_inputs: bpy.props.IntProperty(
        name="Strings", 
        default=2, min=2,
        update=lambda s,c: s.update_sockets()
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.outputs.new('FNSocketString', "Result")
        self.update_sockets()

    def draw_buttons(self, context, layout):
        layout.prop(self, "separator")
        layout.prop(self, "string_inputs")

    def update_sockets(self):
        while len(self.inputs) < self.string_inputs:
            self.inputs.new('FNSocketString', f"String {len(self.inputs) + 1}")
        while len(self.inputs) > self.string_inputs:
            self.inputs.remove(self.inputs[-1])

    def execute(self, **kwargs):
        strings_to_join = []
        for i in range(self.string_inputs):
            socket_id = self.inputs[i].identifier
            s = kwargs.get(socket_id)
            if s:
                strings_to_join.append(s)
        
        result = self.separator.join(strings_to_join)
        return { self.outputs[0].identifier: result }
