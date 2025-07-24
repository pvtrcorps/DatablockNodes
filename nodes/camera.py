import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

class FN_camera(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_camera"
    bl_label = "Camera"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "camera"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        camera_name = kwargs.get("Name")

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{camera_name}_scene"

        camera_data_uuid = self.get_persistent_uuid("camera_data")
        camera_object_uuid = self.get_persistent_uuid("camera_object")

        camera_data_path = f"/root/{camera_name}_data"
        camera_data_proxy = DatablockProxy(path=camera_data_path, parent=root_proxy, fn_uuid=camera_data_uuid)
        camera_data_proxy.properties['datablock_type'] = 'CAMERA'
        camera_data_proxy.properties['name'] = f"{camera_name}_data"

        camera_object_path = f"/root/{camera_name}"
        camera_object_proxy = DatablockProxy(path=camera_object_path, parent=root_proxy, fn_uuid=camera_object_uuid)
        camera_object_proxy.properties['datablock_type'] = 'OBJECT'
        camera_object_proxy.properties['name'] = camera_name
        camera_object_proxy.properties['_fn_relationships'] = {
            'data': camera_data_path,
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}
