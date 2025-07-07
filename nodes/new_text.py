import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketText
from .. import uuid_manager

class FN_new_text(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_text"
    bl_label = "New Text"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketText', "Text")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        text_name = kwargs.get(self.inputs['Name'].identifier, "Text")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_text = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_text:
            if existing_text.name != text_name:
                existing_text.name = text_name
                print(f"  - Updated text name to: '{existing_text.name}'")
            return existing_text
        else:
            new_text = bpy.data.texts.new(name=text_name)
            uuid_manager.set_uuid(new_text)
            print(f"  - Created new Text: {new_text.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_text)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_text)
            
            return new_text
