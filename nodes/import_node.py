import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene
from ..proxy_types import DatablockProxy

class FN_import(FNBaseNode, bpy.types.Node):
    """
    Imports the contents of a .blend file and represents it as a hierarchical scene graph.
    It scans the file without loading it into memory, building a proxy tree of its contents.
    """
    bl_idname = "FN_import"
    bl_label = "Import"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def init(self, context):
        FNBaseNode.init(self, context)
        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        layout.prop(self, "filepath", text="")

    def execute(self, **kwargs):
        output_socket_id = self.outputs[0].identifier

        if not self.filepath or not self.filepath.endswith(".blend"):
            return {output_socket_id: None}

        root_proxy = DatablockProxy(path="/root", fn_uuid=self.fn_output_uuid)
        root_proxy.properties['datablock_type'] = 'SCENE'
        root_proxy.properties['name'] = 'imported_scene'

        try:
            with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
                # Import scenes
                for scene_name in data_from.scenes:
                    scene_path = f"/root/{scene_name}"
                    scene_uuid = self.get_persistent_uuid(f"scene_{scene_name}")
                    scene_proxy = DatablockProxy(path=scene_path, parent=root_proxy, fn_uuid=scene_uuid)
                    scene_proxy.properties['datablock_type'] = 'SCENE'
                    scene_proxy.properties['name'] = scene_name

                # Import top-level collections
                for col_name in data_from.collections:
                    col_path = f"/root/{col_name}"
                    col_uuid = self.get_persistent_uuid(f"collection_{col_name}")
                    col_proxy = DatablockProxy(path=col_path, parent=root_proxy, fn_uuid=col_uuid)
                    col_proxy.properties['datablock_type'] = 'COLLECTION'
                    col_proxy.properties['name'] = col_name

                # Import top-level objects
                for obj_name in data_from.objects:
                    obj_path = f"/root/{obj_name}"
                    obj_uuid = self.get_persistent_uuid(f"object_{obj_name}")
                    obj_proxy = DatablockProxy(path=obj_path, parent=root_proxy, fn_uuid=obj_uuid)
                    obj_proxy.properties['datablock_type'] = 'OBJECT'
                    obj_proxy.properties['name'] = obj_name

        except Exception as e:
            print(f"[FN_import] Error loading library: {e}")
            return {output_socket_id: None}

        return {output_socket_id: root_proxy}
