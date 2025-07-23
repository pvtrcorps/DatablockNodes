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

        # 1. The root of the output is always a Scene proxy.
        scene_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        scene_proxy.properties['datablock_type'] = 'SCENE'
        scene_proxy.properties['name'] = f"{cube_name}_scene"

        # 2. The Object proxy is a child of the Scene proxy.
        object_path = f"/root/{cube_name}"
        object_uuid = self.get_persistent_uuid("object")
        object_proxy = DatablockProxy(path=object_path, parent=scene_proxy, fn_uuid=object_uuid)
        object_proxy.properties['datablock_type'] = 'OBJECT'
        object_proxy.properties['name'] = cube_name
        
        # 3. The Mesh Data proxy is a child of the Object proxy.
        mesh_data_path = f"{object_path}/data"
        mesh_data_uuid = self.get_persistent_uuid("mesh_data")
        mesh_data_proxy = DatablockProxy(path=mesh_data_path, parent=object_proxy, fn_uuid=mesh_data_uuid)
        mesh_data_proxy.properties['datablock_type'] = 'MESH'
        mesh_data_proxy.properties['name'] = f"{cube_name}_data"

        # 4. Establish the relationship from Object to its Data.
        object_proxy.properties['_fn_relationships'] = {
            'data': mesh_data_path,
            'collection_links': ['/root'] # Link the object to the scene collection
        }

        return {self.outputs[0].identifier: scene_proxy}
