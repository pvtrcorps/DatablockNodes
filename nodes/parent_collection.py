import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..engine import query_engine
from .. import logger

class FN_parent_collection(FNBaseNode, bpy.types.Node):
    """Creates parent-child relationships between collections."""
    bl_idname = "FN_parent_collection"
    bl_label = "Parent Collection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketString', "Parent Selection")
        self.inputs.new('FNSocketString', "Children Selection")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        parent_selection_string = kwargs.get("Parent Selection")
        children_selection_string = kwargs.get("Children Selection")

        if not all([scene_root, parent_selection_string, children_selection_string]):
            return {self.outputs[0].identifier: scene_root}

        new_scene_root = scene_root.clone()

        # Resolve the selections in the new, cloned scene
        potential_parents = query_engine.execute_query(new_scene_root, parent_selection_string)
        children_to_parent = query_engine.execute_query(new_scene_root, children_selection_string)

        if not potential_parents:
            logger.log(f"Parent selection '{parent_selection_string}' did not match any proxies.", level='WARNING')
            return {self.outputs[0].identifier: new_scene_root}

        # For simplicity, we use the first matched parent.
        parent_proxy = potential_parents[0]
        if parent_proxy.properties.get('datablock_type') != 'COLLECTION':
            logger.log(f"Target parent '{parent_proxy.path}' is not a COLLECTION.", level='ERROR')
            return {self.outputs[0].identifier: new_scene_root}

        logger.log(f"[ParentCollection] Parenting {len(children_to_parent)} collection(s) to '{parent_proxy.path}'.")

        for child_proxy in children_to_parent:
            if child_proxy.properties.get('datablock_type') != 'COLLECTION':
                continue
            
            # The reparent method handles cloning, repathing, and dependency transfer.
            child_proxy.reparent(parent_proxy)

        return {self.outputs[0].identifier: new_scene_root}
