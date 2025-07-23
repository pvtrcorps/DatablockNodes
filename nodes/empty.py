import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

class FN_empty(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_empty"
    bl_label = "Empty"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "empty"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        empty_name = kwargs.get("Name")

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{empty_name}_scene"

        empty_object_uuid = self.get_persistent_uuid("empty_object")

        empty_object_proxy = DatablockProxy(path=f"/root/{empty_name}", parent=root_proxy, fn_uuid=empty_object_uuid)
        empty_object_proxy.properties['datablock_type'] = 'OBJECT'
        empty_object_proxy.properties['name'] = empty_name
        empty_object_proxy.properties['_fn_relationships'] = {
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}
