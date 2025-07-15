import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketObject, FNSocketMaterial

class FN_set_object_material(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_object_material"
    bl_label = "Set Object Material"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketObject', "Object").is_mutable = True
        self.inputs.new('FNSocketMaterial', "Material")

        self.outputs.new('FNSocketObject', "Object")

    def draw_buttons(self, context, layout):
        pass

    

    def execute(self, **kwargs):
        obj_uuid = kwargs.get(self.inputs['Object'].identifier)
        material_uuid = kwargs.get(self.inputs['Material'].identifier)
        assignments = []

        if obj_uuid and material_uuid:
            assignments.append({
                'target_uuid': obj_uuid,
                'property_name': 'active_material',
                'value_uuid': material_uuid
            })

        return {
            self.outputs[0].identifier: obj_uuid,
            'property_assignments': assignments
        }
