import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketScene, FNSocketObjectList, FNSocketCollectionList

class FN_link_to_scene(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_link_to_scene"
    bl_label = "Link to Scene"

    def init(self, context):
        FNBaseNode.init(self, context)
        scene_socket = self.inputs.new('FNSocketScene', "Scene")
        scene_socket.is_mutable = True
        collections_socket = self.inputs.new('FNSocketCollectionList', "Collections")
        collections_socket.is_mutable = False
        collections_socket.display_shape = 'SQUARE'
        objects_socket = self.inputs.new('FNSocketObjectList', "Objects")
        objects_socket.is_mutable = False
        objects_socket.display_shape = 'SQUARE'
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        target_scene = kwargs.get(self.inputs['Scene'].identifier)
        collections_to_link = kwargs.get(self.inputs['Collections'].identifier)
        objects_to_link = kwargs.get(self.inputs['Objects'].identifier)
        relationships = []

        if not target_scene:
            return {self.outputs[0].identifier: target_scene}

        target_uuid = target_scene

        if collections_to_link:
            if not isinstance(collections_to_link, list):
                collections_to_link = [collections_to_link]
            for col_uuid in collections_to_link:
                if col_uuid:
                    relationships.append((col_uuid, target_uuid, "COLLECTION_SCENE_LINK"))

        if objects_to_link:
            if not isinstance(objects_to_link, list):
                objects_to_link = [objects_to_link]
            for obj_uuid in objects_to_link:
                if obj_uuid:
                    relationships.append((obj_uuid, target_uuid, "OBJECT_SCENE_LINK"))
        
        return {
            self.outputs[0].identifier: target_scene,
            'relationships': relationships
        }