import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketCollection, FNSocketObjectList, FNSocketCollectionList

class FN_link_to_collection(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_link_to_collection"
    bl_label = "Link to Collection"

    def init(self, context):
        FNBaseNode.init(self, context)
        collection_socket = self.inputs.new('FNSocketCollection', "Collection")
        collection_socket.is_mutable = True
        collections_socket = self.inputs.new('FNSocketCollectionList', "Collections")
        collections_socket.is_mutable = False
        collections_socket.display_shape = 'SQUARE'
        objects_socket = self.inputs.new('FNSocketObjectList', "Objects")
        objects_socket.is_mutable = False
        objects_socket.display_shape = 'SQUARE'
        self.outputs.new('FNSocketCollection', "Collection")

    def execute(self, **kwargs):
        target_collection = kwargs.get(self.inputs['Collection'].identifier)
        collections_to_link = kwargs.get(self.inputs['Collections'].identifier)
        objects_to_link = kwargs.get(self.inputs['Objects'].identifier)
        relationships = []

        if not target_collection:
            return {self.outputs[0].identifier: target_collection}

        target_uuid = target_collection

        if collections_to_link:
            if not isinstance(collections_to_link, list):
                collections_to_link = [collections_to_link]
            for col_uuid in collections_to_link:
                if col_uuid:
                    relationships.append((col_uuid, target_uuid, "COLLECTION_CHILD_LINK"))

        if objects_to_link:
            if not isinstance(objects_to_link, list):
                objects_to_link = [objects_to_link]
            for obj_uuid in objects_to_link:
                if obj_uuid:
                    relationships.append((obj_uuid, target_uuid, "COLLECTION_OBJECT_LINK"))
        
        return {
            self.outputs[0].identifier: target_collection,
            'relationships': relationships
        }