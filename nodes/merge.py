
import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene

class FN_merge(FNBaseNode, bpy.types.Node):
    """
    Merges a second scene graph on top of a base scene graph using the
    robust, recursive merge method of the DatablockProxy class.
    """
    bl_idname = "FN_merge"
    bl_label = "Merge"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Base")
        self.inputs.new('FNSocketScene', "Override")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        base_scene = kwargs.get("Base")
        override_scene = kwargs.get("Override")

        if not base_scene:
            return {self.outputs[0].identifier: override_scene}
        if not override_scene:
            return {self.outputs[0].identifier: base_scene}

        # 1. Clone the base scene to work on a non-destructive copy
        new_scene = base_scene.clone()

        # 2. Delegate the entire composition logic to the robust proxy.merge() method
        new_scene.merge(override_scene)

        # 3. Return the composed scene
        return {self.outputs[0].identifier: new_scene}
