import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene

class FN_merge(FNBaseNode, bpy.types.Node):
    """
    Merges multiple scene graphs into a single one. The merge is hierarchical.
    Prims from later inputs will override the properties of prims from earlier inputs
    if they share the same path.
    """
    bl_idname = "FN_merge"
    bl_label = "Merge"

    def init(self, context):
        FNBaseNode.init(self, context)
        # The base scene
        self.inputs.new('FNSocketScene', "Base")
        # The scene to merge on top
        self.inputs.new('FNSocketScene', "Override")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        base_scene_root = kwargs.get("Base")
        override_scene_root = kwargs.get("Override")

        if not base_scene_root and not override_scene_root:
            return {self.outputs[0].identifier: None}
        
        if not base_scene_root:
            return {self.outputs[0].identifier: override_scene_root.clone() if override_scene_root else None}
            
        if not override_scene_root:
            return {self.outputs[0].identifier: base_scene_root.clone()}

        # 1. Clone the base scene to ensure non-destructive workflow
        merged_root = base_scene_root.clone()

        # 2. Call the merge method on the cloned root proxy
        merged_root.merge(override_scene_root)

        # 3. Return the newly composed scene
        return {self.outputs[0].identifier: merged_root}
