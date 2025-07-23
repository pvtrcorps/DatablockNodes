import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketSelection
from .. import logger

class FN_parent(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_parent"
    bl_label = "Parent"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Parent")
        self.inputs.new('FNSocketSelection', "Selection")
        self.inputs.new('FNSocketScene', "Children")
        self.outputs.new('FNSocketScene', "Scene Out")

    def execute(self, **kwargs):
        parent_scene = kwargs.get("Parent")
        selection = kwargs.get("Selection")
        children_scene = kwargs.get("Children")

        if not parent_scene or not parent_scene.children:
            logger.log("[ParentNode] ERROR: 'Parent' scene is empty. Aborting.", level='ERROR')
            return {self.outputs[0].identifier: parent_scene or children_scene}
        
        if not children_scene or not children_scene.children:
            logger.log("[ParentNode] WARNING: 'Children' scene is empty. Nothing to parent.", level='WARNING')
            return {self.outputs[0].identifier: parent_scene}

        logger.log("[ParentNode] Initializing parent operation.")

        # 1. Clone the parent scene to avoid modifying it directly
        new_scene = parent_scene.clone()
        
        # 2. Find the target parent proxy within the new scene
        target_parent_proxy = None
        if selection and selection.raw_expression:
            # A selection is provided, try to find the parent with it.
            logger.log(f"[ParentNode] Selection query received: '{selection.raw_expression}'")
            # This is a simplified evaluation. A real implementation would be more complex.
            # For now, we just look for the first prim whose path matches the glob.
            # Note: This doesn't handle filters yet.
            import fnmatch
            all_prims = new_scene.get_flat_list()
            found_path = None
            for prim in all_prims:
                if fnmatch.fnmatch(prim.path, selection.path_glob):
                    found_path = prim.path
                    break
            
            if found_path:
                target_parent_proxy = new_scene.find_child_by_path(found_path)

            logger.log(f"[ParentNode] Using selection to find parent. Found: {target_parent_proxy.path if target_parent_proxy else 'None'}")
        else:
            # Fallback: We parent to the first object found under the root of the parent scene.
            target_parent_proxy = next((p for p in new_scene.children if p.properties.get('datablock_type') == 'OBJECT'), None)
            logger.log(f"[ParentNode] No selection provided. Falling back to first object: {target_parent_proxy.path if target_parent_proxy else 'None'}")

        if not target_parent_proxy:
            logger.log("[ParentNode] ERROR: No suitable object to parent to was found.", level='ERROR')
            return {self.outputs[0].identifier: new_scene}

        # 3. Iterate over children of the incoming child scene and parent them
        for child_to_parent_proxy in children_scene.children:
            if child_to_parent_proxy.properties.get('datablock_type') != 'OBJECT':
                continue # We only parent objects

            logger.log(f"[ParentNode] Parenting proxy '{child_to_parent_proxy.path}' under '{target_parent_proxy.path}'.")

            # 4. Clone the child proxy and its entire hierarchy
            cloned_child = child_to_parent_proxy.clone()

            # 5. Re-path the cloned child to its new location
            original_path = cloned_child.path
            cloned_child.repath(target_parent_proxy.path)
            logger.log(f"[ParentNode] Path re-written from '{original_path}' to '{cloned_child.path}'.")

            # 6. Add the re-pathed child to the parent's children list
            cloned_child.parent = target_parent_proxy
            target_parent_proxy.children.append(cloned_child)

        return {self.outputs[0].identifier: new_scene}
