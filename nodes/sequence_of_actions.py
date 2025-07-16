import bpy
from .base import FNBaseNode
from ..sockets import FNSocketPulse

def _update_node(self, context):
    self.update_sockets(context)
    self._trigger_update(context)

class FN_sequence_of_actions(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_sequence_of_actions"
    bl_label = "Sequence of Actions"

    action_count: bpy.props.IntProperty(
        name="Actions",
        default=2,
        min=1,
        update=_update_node
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.outputs.new('FNSocketPulse', "Sequence Completed")
        self.update_sockets(context)

    def update_sockets(self, context):
        # Adjust inputs based on action_count
        while len(self.inputs) < self.action_count:
            self.inputs.new('FNSocketPulse', f"Action {len(self.inputs) + 1}")
        while len(self.inputs) > self.action_count:
            self.inputs.remove(self.inputs[-1])

    def draw_buttons(self, context, layout):
        layout.prop(self, "action_count")

    def execute(self, **kwargs):
        # This node's logic is handled by the reconciler.
        # It just needs to pass the pulse through.
        return {self.outputs[0].identifier: True}
