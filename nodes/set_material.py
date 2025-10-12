import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..engine import query_engine
from ..proxy_types import RelationshipType
from .. import logger

class FN_set_material(FNBaseNode, bpy.types.Node):
    """
    Assigns a specified material to selected objects.
    """
    bl_idname = "fn_set_material"
    bl_label = "Set Material"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new(FNSocketScene.bl_idname, "Scene")
        self.inputs.new(FNSocketString.bl_idname, "Selection")
        self.inputs.new(FNSocketString.bl_idname, "Material Name")
        self.outputs.new(FNSocketScene.bl_idname, "Scene")

    def execute(self, **kwargs):
        scene_in = kwargs.get("Scene")
        selection_query = kwargs.get("Selection")
        material_name = kwargs.get("Material Name")

        if not scene_in or not selection_query or not material_name:
            return {self.outputs[0].identifier: scene_in}

        cloned_scene = scene_in.clone()

        material_query = f"/root/materials/*[name={material_name}]"
        material_proxies = query_engine.execute_query(cloned_scene, material_query)

        if not material_proxies:
            logger.log(f"Set Material: Could not find material '{material_name}'.", level='WARNING')
            return {self.outputs[0].identifier: cloned_scene}
        
        material_to_assign = material_proxies[0]

        target_objects = query_engine.execute_query(cloned_scene, selection_query)

        for obj_proxy in target_objects:
            if obj_proxy.properties.get('datablock_type') != 'OBJECT':
                continue
            obj_proxy.clear_relationships(RelationshipType.ACTIVE_MATERIAL)
            obj_proxy.add_relationship(RelationshipType.ACTIVE_MATERIAL, material_to_assign.fn_uuid)

        return {self.outputs[0].identifier: cloned_scene}
