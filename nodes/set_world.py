import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..engine import query_engine
from .. import logger

class FN_set_world(FNBaseNode, bpy.types.Node):
    """
    Assigns a specified world to the scene.
    """
    bl_idname = "fn_set_world"
    bl_label = "Set World"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new(FNSocketScene.bl_idname, "Scene")
        self.inputs.new(FNSocketString.bl_idname, "World Name")
        self.outputs.new(FNSocketScene.bl_idname, "Scene")

    def execute(self, **kwargs):
        scene_in = kwargs.get("Scene")
        world_name = kwargs.get("World Name")

        if not scene_in or not world_name:
            return {self.outputs[0].identifier: scene_in}

        cloned_scene = scene_in.clone()

        world_query = f"/root/worlds/*[name={world_name}]"
        world_proxies = query_engine.execute_query(cloned_scene, world_query)

        if not world_proxies:
            logger.log(f"Set World: Could not find world '{world_name}'.", level='WARNING')
            return {self.outputs[0].identifier: cloned_scene}
        
        world_to_assign = world_proxies[0]

        rels = cloned_scene.properties.setdefault('_fn_relationships', {})
        rels['world'] = world_to_assign.path

        return {self.outputs[0].identifier: cloned_scene}
