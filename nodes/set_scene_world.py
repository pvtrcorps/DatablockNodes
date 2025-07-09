import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketScene, FNSocketWorld

class FN_set_scene_world(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_scene_world"
    bl_label = "Set Scene World"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene").is_mutable = True
        self.inputs.new('FNSocketWorld', "World")

        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        pass

    def update_hash(self, hasher):
        # Hash the input Scene
        scene_input = self.inputs.get('Scene')
        if scene_input and scene_input.is_linked:
            pass
        elif scene_input and hasattr(scene_input, 'default_value'):
            hasher.update(str(scene_input.default_value).encode())

        # Hash the input World
        world_input = self.inputs.get('World')
        if world_input and world_input.is_linked:
            pass
        elif world_input and hasattr(world_input, 'default_value'):
            hasher.update(str(world_input.default_value).encode())

    def execute(self, **kwargs):
        scene = kwargs.get(self.inputs['Scene'].identifier)
        world = kwargs.get(self.inputs['World'].identifier)
        tree = kwargs.get('tree')

        if not scene or not isinstance(scene, bpy.types.Scene):
            print(f"  - Warning: No valid scene provided to {self.name}. Skipping.")
            return None

        if world and isinstance(world, bpy.types.World):
            scene.world = world
            print(f"  - Set world of scene '{scene.name}' to '{world.name}'")
            
            # Register relationship
            new_rel_item = tree.fn_relationships_map.add()
            new_rel_item.node_id = self.fn_node_id
            new_rel_item.source_uuid = uuid_manager.get_uuid(scene)
            new_rel_item.target_uuid = uuid_manager.get_uuid(world)
            new_rel_item.relationship_type = "SCENE_WORLD_ASSIGN"
        else:
            # If no world is provided, clear scene.world and remove any existing relationship
            if scene.world is not None:
                print(f"  - Clearing world of scene '{scene.name}'")
                scene.world = None
            
            # Remove any existing SCENE_WORLD_ASSIGN relationships for this scene
            relationships_to_remove_indices = []
            for i, rel_item in enumerate(tree.fn_relationships_map):
                if rel_item.node_id == self.fn_node_id and rel_item.source_uuid == uuid_manager.get_uuid(scene) and rel_item.relationship_type == "SCENE_WORLD_ASSIGN":
                    relationships_to_remove_indices.append(i)
            
            for i in sorted(relationships_to_remove_indices, reverse=True):
                tree.fn_relationships_map.remove(i)

        return {self.outputs[0].identifier: scene}
