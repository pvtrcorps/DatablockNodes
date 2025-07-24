import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

class FN_cube(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_cube"
    bl_label = "Cube"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "cube"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        cube_name = kwargs.get("Name")

        # The root proxy is the scene container
        root_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{cube_name}_scene"

        # Create sibling proxies for the object and its data
        mesh_data_uuid = self.get_persistent_uuid("mesh_data")
        object_uuid = self.get_persistent_uuid("object")

        mesh_data_path = f"/root/{cube_name}_data"
        mesh_data_proxy = DatablockProxy(path=mesh_data_path, parent=root_proxy, fn_uuid=mesh_data_uuid)
        mesh_data_proxy.properties['datablock_type'] = 'MESH'
        mesh_data_proxy.properties['name'] = f"{cube_name}_data"

        object_path = f"/root/{cube_name}"
        object_proxy = DatablockProxy(path=object_path, parent=root_proxy, fn_uuid=object_uuid)
        object_proxy.properties['datablock_type'] = 'OBJECT'
        object_proxy.properties['name'] = cube_name
        object_proxy.properties['_fn_relationships'] = {
            'data': mesh_data_path,
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}
