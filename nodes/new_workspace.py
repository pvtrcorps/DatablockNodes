import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketWorkSpace
from .. import uuid_manager

class FN_new_workspace(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_workspace"
    bl_label = "New WorkSpace"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.outputs.new('FNSocketWorkSpace', "WorkSpace")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        workspace_name = kwargs.get(self.inputs['Name'].identifier, "WorkSpace")

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        existing_workspace = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

        if existing_workspace:
            if existing_workspace.name != workspace_name:
                existing_workspace.name = workspace_name
                print(f"  - Updated workspace name to: '{existing_workspace.name}'")
            return existing_workspace
        else:
            new_workspace = bpy.data.workspaces.new(name=workspace_name)
            uuid_manager.set_uuid(new_workspace)
            print(f"  - Created new WorkSpace: {new_workspace.name}")

            if map_item:
                map_item.datablock_uuid = uuid_manager.get_uuid(new_workspace)
            else:
                new_map_item = tree.fn_state_map.add()
                new_map_item.node_id = self.fn_node_id
                new_map_item.datablock_uuid = uuid_manager.get_uuid(new_workspace)
            
            return new_workspace
