import bpy
from .base import FNBaseNode
from ..sockets import FNSocketExecute, FNSocketSceneList

class FN_output_scenes(FNBaseNode):
    bl_idname = 'FN_output_scenes'
    bl_label = 'Output Scenes'

    def init(self, context):
        self.inputs.new(FNSocketExecute.bl_idname, "Run")
        scene_list_socket = self.inputs.new(FNSocketSceneList.bl_idname, "Scene List")
        scene_list_socket.display_shape = 'SQUARE'

    def execute(self, **kwargs):
        # This node primarily acts as a trigger for the reconciler
        # The actual scene output will be handled by the reconciler based on the connected Scene List
        print("[Output Scenes Node] Executing...")
        scenes = kwargs.get("Scene List", [])
        print(f"[Output Scenes Node] Received {len(scenes)} scenes.")
        # No direct output from this node, as it's a terminal node
        return None
