import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy
from .. import state_manager

class FN_scene(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_scene"
    bl_label = "Scene"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "Scene"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        # The user-facing name for the Blender scene datablock.
        scene_name = kwargs.get("Name") or "Scene"
        
        # The internal root path is now fixed, aligning with Gaffer's /world concept.
        root_path = "/root"

        root_proxy = DatablockProxy(path=root_path, fn_uuid=self.fn_output_uuid)

        # Get the default scene properties and add them directly to the root proxy
        scene_props = state_manager.define_new_state('SCENE', scene_name)
        root_proxy.properties.update(scene_props)

        return {self.outputs[0].identifier: root_proxy}
