
import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketScene
from .. import uuid_manager

class FN_new_scene(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_scene"
    bl_label = "New Scene"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        scene_name = kwargs.get(self.inputs['Name'].identifier, "Scene")

        # This node is a creator, so it's always responsible for one datablock.
        # We check the state map to see if it already manages one.
        print(f"\n[FN_new_scene] Node ID: {self.fn_node_id}")
        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        print(f"[FN_new_scene] Map Item found: {map_item is not None}")
        
        existing_scene = None
        if map_item:
            print(f"[FN_new_scene] Map Item Datablock UUID: {map_item.datablock_uuid}")
            existing_scene = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid)
        
        print(f"[FN_new_scene] Existing scene found: {existing_scene is not None}")

        if existing_scene:
            # If the scene exists, we just update its name if needed.
            if existing_scene.name != scene_name:
                existing_scene.name = scene_name
                print(f"  - Updated scene name to: '{existing_scene.name}'")
            return existing_scene
        else:
            # If no scene exists, create a new one.
            new_scene = bpy.data.scenes.new(name=scene_name)
            uuid_manager.set_uuid(new_scene)
            print(f"  - Created new Scene: {new_scene.name}")

            # Register it in the state map.
            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_scene)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_scene)
            
            return new_scene
