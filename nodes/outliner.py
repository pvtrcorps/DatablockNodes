import bpy
import json
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene
from ..proxy_types import DatablockProxy
from .. import logger

class OutlinerListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    path: bpy.props.StringProperty(name="Path")
    indent_level: bpy.props.IntProperty(name="Indent Level")

class FN_UL_outliner_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        indent = "    " * item.indent_level
        layout.label(text=f"{indent}/{item.name}")

class FN_OT_outliner_copy_path(bpy.types.Operator):
    bl_idname = "fn.outliner_copy_path"
    bl_label = "Copy Path"
    bl_description = "Copy the selected item's path to the clipboard"

    @classmethod
    def poll(cls, context):
        node = context.node
        return node and hasattr(node, 'bl_idname') and node.bl_idname == 'FN_outliner' and node.outliner_items and node.outliner_index >= 0

    def execute(self, context):
        node = context.node
        if node and node.outliner_items and node.outliner_index >= 0:
            selected_item = node.outliner_items[node.outliner_index]
            context.window_manager.clipboard = selected_item.path
            self.report({'INFO'}, f"Path copied: {selected_item.path}")
        return {'FINISHED'}

def _update_selection(self, context):
    self.selected_proxy_properties = ""
    if self.scene_cache_json and self.outliner_index >= 0 and self.outliner_index < len(self.outliner_items):
        try:
            scene_data = json.loads(self.scene_cache_json)
            root_proxy = DatablockProxy.from_dict(scene_data)
            selected_path = self.outliner_items[self.outliner_index].path
            selected_proxy = root_proxy.find_child_by_path(selected_path)
            if selected_proxy:
                self.selected_proxy_properties = json.dumps(selected_proxy.properties, indent=2)
        except (json.JSONDecodeError, TypeError):
            self.selected_proxy_properties = '{"error": "Could not decode scene cache."}'

class FN_outliner(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_outliner"
    bl_label = "Outliner"

    outliner_items: bpy.props.CollectionProperty(type=OutlinerListItem)
    outliner_index: bpy.props.IntProperty(update=_update_selection)
    scene_cache_json: bpy.props.StringProperty(default="")
    selected_proxy_properties: bpy.props.StringProperty(default="")

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_in = kwargs.get("Scene")
        if scene_in:
            self.scene_cache_json = json.dumps(scene_in.to_dict())
        else:
            self.scene_cache_json = ""

        self.outliner_items.clear()
        if scene_in:
            def add_proxy_to_list(proxy, level):
                item = self.outliner_items.add()
                item.name = proxy.path.split('/')[-1] or proxy.path
                item.path = proxy.path
                item.indent_level = level
                for child in proxy.children:
                    add_proxy_to_list(child, level + 1)
            add_proxy_to_list(scene_in, 0)

        _update_selection(self, bpy.context)
        return {self.outputs[0].identifier: scene_in}

    def draw_proxy_properties(self, layout, props_dict):
        def draw_recursive(d, parent_layout, level=0):
            indent_str = "  " * level
            if not isinstance(d, dict):
                parent_layout.label(text=f"{indent_str}{d}")
                return

            for key, value in d.items():
                if isinstance(value, dict):
                    box = parent_layout.box()
                    box.label(text=f"{indent_str}{key}:")
                    draw_recursive(value, box, level + 1)
                elif isinstance(value, list):
                    box = parent_layout.box()
                    box.label(text=f"{indent_str}{key}:")
                    col = box.column(align=True)
                    for i, item in enumerate(value):
                        draw_recursive({f"[{i}]": item}, col, level + 1)
                else:
                    row = parent_layout.row(align=True)
                    row.label(text=f"{indent_str}{key}:")
                    row.label(text=str(value))
        draw_recursive(props_dict, layout)

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.template_list("FN_UL_outliner_list", "", self, "outliner_items", self, "outliner_index")
        col = row.column(align=True)
        col.operator(FN_OT_outliner_copy_path.bl_idname, text="", icon='COPYDOWN')
        
        if self.selected_proxy_properties:
            try:
                props = json.loads(self.selected_proxy_properties)
                inspector_box = layout.box()
                if self.outliner_index >= 0 and self.outliner_index < len(self.outliner_items):
                    selected_item = self.outliner_items[self.outliner_index]
                    inspector_box.label(text=f"Inspector: {selected_item.name}", icon='INFO')
                self.draw_proxy_properties(inspector_box, props)
            except json.JSONDecodeError:
                layout.label(text="Error decoding properties.", icon='ERROR')