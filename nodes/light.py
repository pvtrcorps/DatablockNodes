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

        # 1. The root of the output is always a Scene proxy.
        scene_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        scene_proxy.properties['datablock_type'] = 'SCENE'
        scene_proxy.properties['name'] = f"{light_name}_scene"

        # 2. The Object proxy is a child of the Scene proxy.
        object_path = f"/root/{light_name}"
        object_uuid = self.get_persistent_uuid("light_object")
        object_proxy = DatablockProxy(path=object_path, parent=scene_proxy, fn_uuid=object_uuid)
        object_proxy.properties['datablock_type'] = 'OBJECT'
        object_proxy.properties['name'] = light_name

        # 3. The Light Data proxy is a child of the Object proxy.
        light_data_path = f"{object_path}/data"
        light_data_uuid = self.get_persistent_uuid("light_data")
        light_data_proxy = DatablockProxy(path=light_data_path, parent=object_proxy, fn_uuid=light_data_uuid)
        light_data_proxy.properties['datablock_type'] = 'LIGHT'
        light_data_proxy.properties['name'] = f"{light_name}_data"
        light_data_proxy.properties['type'] = self.light_type
        light_data_proxy.properties['energy'] = self.energy

        # 4. Establish the relationship from Object to its Data.
        object_proxy.properties['_fn_relationships'] = {
            'data': light_data_path,
            'collection_links': ['/root']
        }

        return {self.outputs[0].identifier: scene_proxy}
