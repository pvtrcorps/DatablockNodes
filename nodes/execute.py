import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketExecute

class FN_execute(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_execute"
    bl_label = "Execute"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.outputs.new(FNSocketExecute.bl_idname, "Execute")

    def execute(self, **kwargs):
        # This node simply outputs a signal to trigger execution in connected nodes.
        # The actual value doesn't matter as much as the fact that it's executed.
        print(f"[Execute Node] Node '{self.name}' triggered.")
        return True
