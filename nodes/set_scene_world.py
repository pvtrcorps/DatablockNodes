import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketScene, FNSocketWorld

class FN_set_scene_world(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_scene_world"
    bl_label = "Set Scene World"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene").is_mutable = True
        self.inputs.new('FNSocketWorld', "World")

        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        pass

    

    def execute(self, **kwargs):
        scene_uuid = kwargs.get(self.inputs['Scene'].identifier)
        world_uuid = kwargs.get(self.inputs['World'].identifier)
        assignments = []

        if scene_uuid and world_uuid:
            assignments.append({
                'target_uuid': scene_uuid,
                'property_name': 'world',
                'value_type': 'UUID',
                'value_uuid': world_uuid,
                'value_json': '' # Not used for UUID assignments
            })

        return {
            self.outputs[0].identifier: scene_uuid,
            'property_assignments': assignments
        }
