import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

class FN_scene(FNBaseNode, bpy.types.Node):
    """
    The most basic source node. It creates and outputs the root of a new, empty scene graph.
    This is the starting point for any composition.
    """
    bl_idname = "FN_scene"
    bl_label = "Scene"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_name = kwargs.get("Name") or "scene"

        # Create the root proxy for the new scene graph.
        # The path is simply "/root". It has no parent.
        root_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        
        # Set the datablock type for the root prim to be a Blender Scene.
        # This tells the reconciler to create a bpy.types.Scene datablock.
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = scene_name

        # Return the root proxy on the output socket.
        return { self.outputs[0].identifier: root_proxy }
