import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..engine import utils

class FN_parent_collection(FNBaseNode, bpy.types.Node):
    """Creates parent-child relationships between collections."""
    bl_idname = "FN_parent_collection"
    bl_label = "Parent Collection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketString', "Parent Collections")
        self.inputs.new('FNSocketString', "Child Collections")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        parent_names_str = kwargs.get("Parent Collections")
        child_names_str = kwargs.get("Child Collections")

        if not scene_root or not parent_names_str or not child_names_str:
            return {self.outputs[0].identifier: scene_root}

        new_scene_root = scene_root.clone()
        parent_names = utils.parse_multi_target_string(parent_names_str)
        child_names = utils.parse_multi_target_string(child_names_str)

        for child_name in child_names:
            child_path = f"/{child_name}"
            child_prim = new_scene_root.find_child_by_path(child_path)
            if not child_prim or child_prim.properties.get('datablock_type') != 'COLLECTION':
                continue

            for parent_name in parent_names:
                parent_path = f"/{parent_name}"
                parent_prim = new_scene_root.find_child_by_path(parent_path)
                if not parent_prim or parent_prim.properties.get('datablock_type') != 'COLLECTION':
                    continue
                
                # This node defines a single, explicit parent for a collection.
                # Therefore, we clear existing links and set the new one.
                relationships = child_prim.properties.setdefault('_fn_relationships', {})
                links = relationships.setdefault('collection_links', [])
                links.clear()
                links.append(parent_path)

        return {self.outputs[0].identifier: new_scene_root}
