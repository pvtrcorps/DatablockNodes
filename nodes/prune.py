import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketSelection
from ..engine import utils
from ..query_types import FNSelectionQuery

class FN_prune(FNBaseNode, bpy.types.Node):
    """
    Removes branches from the scene graph based on a Selection.
    """
    bl_idname = "FN_prune"
    bl_label = "Prune"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketSelection', "Selection")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        selection_query = kwargs.get("Selection")

        if not scene_root:
            return {self.outputs[0].identifier: scene_root}

        # If no selection is provided, create a query that selects everything.
        if not selection_query:
            selection_query = FNSelectionQuery(raw_expression="*", path_glob="*", filters=[])

        # Clone the scene to work on a copy
        new_scene_root = scene_root.clone()

        # Resolve the selection to get the target prims
        prims_to_prune = utils.resolve_selection(new_scene_root, selection_query)

        for prim in prims_to_prune:
            if prim.parent:
                # It's crucial to remove from the cloned parent in the new scene graph
                try:
                    prim.parent.children.remove(prim)
                except ValueError:
                    # This can happen if a parent of a selected prim was also pruned.
                    # It's safe to ignore.
                    pass

        return {self.outputs[0].identifier: new_scene_root}
