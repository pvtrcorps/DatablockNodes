import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..engine import query_engine
from .. import logger

class FN_prune(FNBaseNode, bpy.types.Node):
    """
    Removes branches from the scene graph based on a query,
    intelligently removing any orphaned data-blocks.
    """
    bl_idname = "FN_prune"
    bl_label = "Prune"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketString', "Selection")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        selection_string = kwargs.get("Selection")

        if not scene_root:
            return {self.outputs[0].identifier: scene_root}

        if not selection_string:
            logger.log("[PruneNode] No selection provided. Passing scene through untouched.")
            return {self.outputs[0].identifier: scene_root}

        # Clone the scene to work on a non-destructive copy
        new_scene_root = scene_root.clone()

        # Use the new query engine to get the target proxies
        proxies_to_prune = query_engine.execute_query(new_scene_root, selection_string)

        if proxies_to_prune:
            logger.log(f"[PruneNode] Pruning {len(proxies_to_prune)} proxies matching '{selection_string}'.")

        for proxy in proxies_to_prune:
            # The prune method on the proxy handles detaching from the parent
            # and cleaning up any orphaned dependencies.
            proxy.prune()

        return {self.outputs[0].identifier: new_scene_root}
