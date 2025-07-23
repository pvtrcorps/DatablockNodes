import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketSceneList

class FN_create_scene_list(FNBaseNode, bpy.types.Node):
    """
    Collects multiple scene graphs into a single list for batch processing
    by an Executor node (e.g., Batch Render).
    """
    bl_idname = "FN_create_scene_list"
    bl_label = "Create Scene List"

    # The number of scene inputs can be changed by the user
    scene_inputs: bpy.props.IntProperty(name="Scenes", default=1, min=1, update=lambda s,c: s.update_sockets())

    def init(self, context):
        FNBaseNode.init(self, context)
        self.outputs.new('FNSocketSceneList', "Scene List")
        self.update_sockets()

    def draw_buttons(self, context, layout):
        layout.prop(self, "scene_inputs")

    def update_sockets(self):
        # Add or remove inputs based on the scene_inputs property
        while len(self.inputs) < self.scene_inputs:
            self.inputs.new('FNSocketScene', f"Scene {len(self.inputs) + 1}")
        while len(self.inputs) > self.scene_inputs:
            self.inputs.remove(self.inputs[-1])

    def execute(self, **kwargs):
        scene_list = []
        for i in range(self.scene_inputs):
            socket_id = self.inputs[i].identifier
            scene_root = kwargs.get(socket_id)
            if scene_root:
                scene_list.append(scene_root)
        
        return {self.outputs[0].identifier: scene_list}
