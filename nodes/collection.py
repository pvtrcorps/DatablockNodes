import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

class FN_collection(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_collection"
    bl_label = "Collection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "Collection"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        collection_name = kwargs.get("Name")
        scene_name = f"{collection_name}_scene"
        scene_path = f"/{scene_name}"

        root_proxy = DatablockProxy(path=scene_path, fn_uuid=self.fn_output_uuid)
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = scene_name

        collection_uuid = self.get_persistent_uuid("collection")
        collection_path = f"{scene_path}/collections/{collection_name}"

        collection_proxy = DatablockProxy(path=collection_path, parent=root_proxy, fn_uuid=collection_uuid)
        collection_proxy.properties['datablock_type'] = 'COLLECTION'
        collection_proxy.properties['name'] = collection_name
        collection_proxy.properties['is_default_collection_prim'] = True # For easy finding
        collection_proxy.properties['_fn_relationships'] = {
            'collection_links': [scene_path]
        }

        return {self.outputs[0].identifier: root_proxy}
