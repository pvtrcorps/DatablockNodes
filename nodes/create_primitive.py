"""
Node to procedurally create primitive objects.
"""
import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

def _update_node(self, context):
    self.id_data.update_tag()

class FN_create_primitive(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_create_primitive"
    bl_label = "Create Primitive"

    primitive_type: bpy.props.EnumProperty(
        name="Primitive Type",
        items=[
            ('MESH', "Mesh", ""),
            ('LIGHT', "Light", ""),
            ('CAMERA', "Camera", ""),
        ],
        default='MESH',
        update=_update_node
    )

    mesh_type: bpy.props.EnumProperty(
        name="Mesh Type",
        items=[
            ('CUBE', "Cube", ""),
            ('SPHERE', "Sphere", ""),
        ],
        default='CUBE',
        update=_update_node
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "primitive"
        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        layout.prop(self, "primitive_type", text="")
        if self.primitive_type == 'MESH':
            layout.prop(self, "mesh_type", text="")

    def execute(self, **kwargs):
        if self.primitive_type == 'MESH':
            if self.mesh_type == 'CUBE':
                return self._execute_cube(**kwargs)
            elif self.mesh_type == 'SPHERE':
                return self._execute_sphere(**kwargs)
        elif self.primitive_type == 'LIGHT':
            return self._execute_light(**kwargs)
        elif self.primitive_type == 'CAMERA':
            return self._execute_camera(**kwargs)
        return {self.outputs[0].identifier: None}

    def _execute_sphere(self, **kwargs):
        # Placeholder for sphere logic
        return self._execute_cube(**kwargs) # For now, just return a cube

    def _execute_light(self, **kwargs):
        name = kwargs.get("Name")

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.get_persistent_uuid(self.primitive_type))
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{name}_scene"

        light_data_uuid = self.get_persistent_uuid(f"LIGHT_data")
        object_uuid = self.get_persistent_uuid(f"LIGHT_object")

        light_data_path = f"/root/{name}_data"
        light_data_proxy = DatablockProxy(path=light_data_path, parent=root_proxy, fn_uuid=light_data_uuid)
        light_data_proxy.properties['datablock_type'] = 'LIGHT'
        light_data_proxy.properties['name'] = f"{name}_data"
        # TODO: Add sockets for light type and energy
        light_data_proxy.properties['type'] = 'POINT' 
        light_data_proxy.properties['energy'] = 100.0

        object_path = f"/root/{name}"
        object_proxy = DatablockProxy(path=object_path, parent=root_proxy, fn_uuid=object_uuid)
        object_proxy.properties['datablock_type'] = 'OBJECT'
        object_proxy.properties['name'] = name
        object_proxy.properties['_fn_relationships'] = {
            'data': light_data_path,
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}

    def _execute_camera(self, **kwargs):
        name = kwargs.get("Name")

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.get_persistent_uuid(self.primitive_type))
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{name}_scene"

        camera_data_uuid = self.get_persistent_uuid(f"CAMERA_data")
        object_uuid = self.get_persistent_uuid(f"CAMERA_object")

        camera_data_path = f"/root/{name}_data"
        camera_data_proxy = DatablockProxy(path=camera_data_path, parent=root_proxy, fn_uuid=camera_data_uuid)
        camera_data_proxy.properties['datablock_type'] = 'CAMERA'
        camera_data_proxy.properties['name'] = f"{name}_data"

        object_path = f"/root/{name}"
        object_proxy = DatablockProxy(path=object_path, parent=root_proxy, fn_uuid=object_uuid)
        object_proxy.properties['datablock_type'] = 'OBJECT'
        object_proxy.properties['name'] = name
        object_proxy.properties['_fn_relationships'] = {
            'data': camera_data_path,
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}

    def _execute_cube(self, **kwargs):
        name = kwargs.get("Name")

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.get_persistent_uuid(self.primitive_type))
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{name}_scene"

        mesh_data_uuid = self.get_persistent_uuid(f"CUBE_data")
        object_uuid = self.get_persistent_uuid(f"CUBE_object")

        mesh_data_path = f"/root/{name}_data"
        mesh_data_proxy = DatablockProxy(path=mesh_data_path, parent=root_proxy, fn_uuid=mesh_data_uuid)
        mesh_data_proxy.properties['datablock_type'] = 'MESH'
        mesh_data_proxy.properties['name'] = f"{name}_data"

        verts = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), 
                 (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
        faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 4, 7, 3), 
                 (1, 5, 6, 2), (0, 1, 5, 4), (3, 2, 6, 7)]
        
        mesh_data_proxy.properties['_fn_geometry_data'] = {
            'vertices': verts,
            'edges': [],
            'faces': faces
        }

        object_path = f"/root/{name}"
        object_proxy = DatablockProxy(path=object_path, parent=root_proxy, fn_uuid=object_uuid)
        object_proxy.properties['datablock_type'] = 'OBJECT'
        object_proxy.properties['name'] = name
        object_proxy.properties['_fn_relationships'] = {
            'data': mesh_data_path,
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}
