import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketObject, FNSocketObjectList

class FN_set_object_parent(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_object_parent"
    bl_label = "Set Object Parent"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketObject', "Parent")
        self.inputs.new('FNSocketObjectList', "Childs").is_mutable = True
        self.inputs['Childs'].display_shape = 'SQUARE'

        self.outputs.new('FNSocketObjectList', "Parent and Childs").is_mutable = False
        self.outputs['Parent and Childs'].display_shape = 'SQUARE'

    def draw_buttons(self, context, layout):
        pass

    

    def execute(self, **kwargs):
        parent_uuid = kwargs.get(self.inputs['Parent'].identifier)
        child_uuids = kwargs.get(self.inputs['Childs'].identifier)
        assignments = []

        if not child_uuids:
            return {self.outputs[0].identifier: []}

        if not isinstance(child_uuids, list):
            child_uuids = [child_uuids]

        processed_childs = []
        for child_uuid in child_uuids:
            if not child_uuid:
                continue

            if parent_uuid:
                assignments.append({
                    'target_uuid': child_uuid,
                    'property_name': 'parent',
                    'value_uuid': parent_uuid
                })
            
            processed_childs.append(child_uuid)

        output_list = []
        if parent_uuid:
            output_list.append(parent_uuid)
        output_list.extend(processed_childs)

        return {
            self.outputs[0].identifier: output_list,
            'property_assignments': assignments
        }
