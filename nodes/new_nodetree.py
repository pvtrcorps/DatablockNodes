import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketNodeTree
from .. import uuid_manager

class FN_new_nodetree(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_nodetree"
    bl_label = "New Node Tree"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketNodeTree', "Node Tree")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        nodetree_name = kwargs.get(self.inputs['Name'].identifier, "Node Tree")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_nodetree = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_nodetree:
            if existing_nodetree.name != nodetree_name:
                existing_nodetree.name = nodetree_name
                print(f"  - Updated node tree name to: '{existing_nodetree.name}'")
            return existing_nodetree
        else:
            new_nodetree = bpy.data.node_groups.new(name=nodetree_name, type='ShaderNodeTree') # Default to ShaderNodeTree
            uuid_manager.set_uuid(new_nodetree)
            print(f"  - Created new Node Tree: {new_nodetree.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_nodetree)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_nodetree)
            
            return new_nodetree
