import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString

class FN_string(FNBaseNode, bpy.types.Node):
    """An input node for a simple String value."""
    bl_idname = "FN_string"
    bl_label = "String"

    value: bpy.props.StringProperty(
        name="Value",
        update=lambda s,c: s.id_data.update_tag()
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.outputs.new('FNSocketString', "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "value", text="")

    def execute(self, **kwargs):
        return { self.outputs[0].identifier: self.value }
