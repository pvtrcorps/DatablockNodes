import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketLight
from .. import uuid_manager

class FN_new_light(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_light"
    bl_label = "New Light"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketLight', "Light")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        light_name = kwargs.get(self.inputs['Name'].identifier, "Light")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_light = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_light:
            if existing_light.name != light_name:
                existing_light.name = light_name
                print(f"  - Updated light name to: '{existing_light.name}'")
            return existing_light
        else:
            new_light = bpy.data.lights.new(name=light_name, type='POINT')
            uuid_manager.set_uuid(new_light)
            print(f"  - Created new Light: {new_light.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_light)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_light)
            
            return new_light
