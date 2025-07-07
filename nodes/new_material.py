import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketMaterial
from .. import uuid_manager

class FN_new_material(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_material"
    bl_label = "New Material"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketMaterial', "Material")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        material_name = kwargs.get(self.inputs['Name'].identifier, "Material")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_material = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_material:
            if existing_material.name != material_name:
                existing_material.name = material_name
                print(f"  - Updated material name to: '{existing_material.name}'")
            return existing_material
        else:
            new_material = bpy.data.materials.new(name=material_name)
            uuid_manager.set_uuid(new_material)
            print(f"  - Created new Material: {new_material.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_material)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_material)
            
            return new_material
