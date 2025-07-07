import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketMesh
from .. import uuid_manager

class FN_new_mesh(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_mesh"
    bl_label = "New Mesh"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketMesh', "Mesh")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        mesh_name = kwargs.get(self.inputs['Name'].identifier, "Mesh")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_mesh = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_mesh:
            if existing_mesh.name != mesh_name:
                existing_mesh.name = mesh_name
                print(f"  - Updated mesh name to: '{existing_mesh.name}'")
            return existing_mesh
        else:
            new_mesh = bpy.data.meshes.new(name=mesh_name)
            uuid_manager.set_uuid(new_mesh)
            print(f"  - Created new Mesh: {new_mesh.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_mesh)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_mesh)
            
            return new_mesh
