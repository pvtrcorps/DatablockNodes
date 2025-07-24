import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..proxy_types import DatablockProxy

class FN_light(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_light"
    bl_label = "Light"

    light_type: bpy.props.EnumProperty(
        name="Light Type",
        items=[
            ('POINT', "Point", ""),
            ('SUN', "Sun", ""),
            ('SPOT', "Spot", ""),
            ('AREA', "Area", ""),
        ],
        default='POINT',
    )
    energy: bpy.props.FloatProperty(name="Energy", default=100.0)

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name").default_value = "light"
        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        layout.prop(self, "light_type", text="")
        layout.prop(self, "energy")

    def execute(self, **kwargs):
        light_name = kwargs.get("Name")

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = f"{light_name}_scene"

        light_data_uuid = self.get_persistent_uuid("light_data")
        light_object_uuid = self.get_persistent_uuid("light_object")

        light_data_path = f"/root/{light_name}_data"
        light_data_proxy = DatablockProxy(path=light_data_path, parent=root_proxy, fn_uuid=light_data_uuid)
        light_data_proxy.properties['datablock_type'] = 'LIGHT'
        light_data_proxy.properties['name'] = f"{light_name}_data"
        light_data_proxy.properties['type'] = self.light_type
        light_data_proxy.properties['energy'] = self.energy

        light_object_path = f"/root/{light_name}"
        light_object_proxy = DatablockProxy(path=light_object_path, parent=root_proxy, fn_uuid=light_object_uuid)
        light_object_proxy.properties['datablock_type'] = 'OBJECT'
        light_object_proxy.properties['name'] = light_name
        light_object_proxy.properties['_fn_relationships'] = {
            'data': light_data_path,
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: root_proxy}
