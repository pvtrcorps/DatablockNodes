import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from .. import logger
from ..engine import query_engine

class FN_parent(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_parent"
    bl_label = "Parent"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketString', "Parent Selection")
        self.inputs.new('FNSocketScene', "Children")
        self.outputs.new('FNSocketScene', "Scene Out")

    def execute(self, **kwargs):
        scene = kwargs.get("Scene")
        parent_selection_string = kwargs.get("Parent Selection")
        children_scene = kwargs.get("Children")

        if not scene:
            logger.log("'Scene' input is not connected. Returning children if available.", level='ERROR')
            return {self.outputs[0].identifier: children_scene}
        
        if not children_scene or not children_scene.children:
            logger.log("'Children' scene is empty. Nothing to parent.", level='WARNING')
            return {self.outputs[0].identifier: scene}

        if not parent_selection_string:
            logger.log("'Parent Selection' is not defined. Aborting.", level='ERROR')
            return {self.outputs[0].identifier: scene}

        # 1. Clone the main scene to ensure a non-destructive workflow
        new_scene = scene.clone()
        
        # 2. Find the target parent proxy within the newly cloned scene using the query engine
        potential_parents = query_engine.execute_query(new_scene, parent_selection_string)
        if not potential_parents:
            logger.log(f"Selection '{parent_selection_string}' did not match any proxies.", level='ERROR')
            return {self.outputs[0].identifier: new_scene}
        
        # For parenting, we can only have one parent. We take the first result.
        target_parent_proxy = potential_parents[0]

        if target_parent_proxy.properties.get('datablock_type') != 'OBJECT':
            logger.log(f"Target parent '{target_parent_proxy.path}' is not an OBJECT.", level='ERROR')
            return {self.outputs[0].identifier: new_scene}

        # 3. Identify top-level OBJECT proxies in the 'Children' scene to be parented
        child_objects_to_parent = []
        for child_proxy in children_scene.children:
            if child_proxy.properties.get('datablock_type') == 'OBJECT':
                child_objects_to_parent.append(child_proxy)
            # Also check one level deep for the common /<scene>/objects namespace
            elif child_proxy.path.endswith("/objects"):
                child_objects_to_parent.extend(child_proxy.children)

        if not child_objects_to_parent:
            logger.log("No top-level OBJECT proxies found in 'Children' scene to parent.", level='WARNING')
            return {self.outputs[0].identifier: new_scene}

        logger.log(f"[ParentNode] Parenting {len(child_objects_to_parent)} proxies to '{target_parent_proxy.path}'.")

        # 4. Execute the reparent operation for each child
        for child_to_reparent in child_objects_to_parent:
            # The reparent method handles cloning, repathing, and dependency transfer.
            child_to_reparent.reparent(target_parent_proxy)

        return {self.outputs[0].identifier: new_scene}
