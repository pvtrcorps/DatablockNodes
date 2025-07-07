import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketCamera
from .. import uuid_manager

class FN_new_camera(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_camera"
    bl_label = "New Camera"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketCamera', "Camera")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        camera_name = kwargs.get(self.inputs['Name'].identifier, "Camera")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_camera = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_camera:
            if existing_camera.name != camera_name:
                existing_camera.name = camera_name
                print(f"  - Updated camera name to: '{existing_camera.name}'")
            return existing_camera
        else:
            new_camera = bpy.data.cameras.new(name=camera_name)
            uuid_manager.set_uuid(new_camera)
            print(f"  - Created new Camera: {new_camera.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_camera)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_camera)
            
            return new_camera
