import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketWorld
from .. import uuid_manager

class FN_new_world(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_world"
    bl_label = "New World"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketWorld', "World")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        world_name = kwargs.get(self.inputs['Name'].identifier, "World")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_world = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_world:
            if existing_world.name != world_name:
                existing_world.name = world_name
                print(f"  - Updated world name to: '{existing_world.name}'")
            return existing_world
        else:
            new_world = bpy.data.worlds.new(name=world_name)
            uuid_manager.set_uuid(new_world)
            print(f"  - Created new World: {new_world.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_world)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_world)
            
            return new_world
