import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketCollection
from .. import uuid_manager

class FN_new_collection(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_collection"
    bl_label = "New Collection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketCollection', "Collection")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        collection_name = kwargs.get(self.inputs['Name'].identifier, "Collection")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_collection = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_collection:
            if existing_collection.name != collection_name:
                existing_collection.name = collection_name
                print(f"  - Updated collection name to: '{existing_collection.name}'")
            return existing_collection
        else:
            new_collection = bpy.data.collections.new(name=collection_name)
            uuid_manager.set_uuid(new_collection)
            print(f"  - Created new Collection: {new_collection.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_collection)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_collection)
            
            return new_collection
