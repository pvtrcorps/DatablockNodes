import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketImage
from .. import uuid_manager

class FN_new_image(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_image"
    bl_label = "New Image"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketImage', "Image")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        image_name = kwargs.get(self.inputs['Name'].identifier, "Image")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_image = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_image:
            if existing_image.name != image_name:
                existing_image.name = image_name
                print(f"  - Updated image name to: '{existing_image.name}'")
            return existing_image
        else:
            # For simplicity, creating a new blank image. More advanced options could be added later.
            new_image = bpy.data.images.new(name=image_name, width=1024, height=1024)
            uuid_manager.set_uuid(new_image)
            print(f"  - Created new Image: {new_image.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_image)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_image)
            
            return new_image
