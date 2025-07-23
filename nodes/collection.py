import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

class FN_collection(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_collection"
    bl_label = "Collection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "collection"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        collection_name = kwargs.get("Name")

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{collection_name}_scene"

        collection_uuid = self.get_persistent_uuid("collection")

        collection_proxy = DatablockProxy(path=f"/root/{collection_name}", parent=root_proxy, fn_uuid=collection_uuid)
        collection_proxy.properties['datablock_type'] = 'COLLECTION'
        collection_proxy.properties['name'] = collection_name
        collection_proxy.properties['is_default_collection_prim'] = True # For easy finding
        collection_proxy.properties['_fn_relationships'] = {
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}
