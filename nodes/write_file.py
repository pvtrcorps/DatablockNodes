import bpy
from .base import FNBaseNode
from ..sockets import (
    FNSocketString, FNSocketBool,
    FNSocketSceneList, FNSocketObjectList, FNSocketCollectionList, FNSocketWorldList,
    FNSocketCameraList, FNSocketImageList, FNSocketLightList, FNSocketMaterialList,
    FNSocketMeshList, FNSocketNodeTreeList, FNSocketTextList, FNSocketWorkSpaceList,
    FNSocketStringList, FNSocketViewLayerList
)

# Define which datablock types the node will handle and their corresponding socket types
_datablock_types_to_write = {
    'objects': 'FNSocketObjectList',
    'collections': 'FNSocketCollectionList',
    'scenes': 'FNSocketSceneList',
    'materials': 'FNSocketMaterialList',
    'meshes': 'FNSocketMeshList',
    'lights': 'FNSocketLightList',
    'cameras': 'FNSocketCameraList',
    'images': 'FNSocketImageList',
    'node_groups': 'FNSocketNodeTreeList',
    'texts': 'FNSocketTextList',
    'worlds': 'FNSocketWorldList',
    'workspaces': 'FNSocketWorkSpaceList',
    # Add more as needed from bpy.data
}

class FN_write_file(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_write_file"
    bl_label = "Write File"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.manages_scene_datablock = False # This node performs an action, it doesn't define a scene state

        # Clear existing inputs/outputs to re-add them
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add input sockets for file path and options
        self.inputs.new('FNSocketString', "File Path").subtype = 'FILE_PATH'
        self.inputs.new('FNSocketBool', "Overwrite").default_value = False

        # Add input sockets for all supported datablock types
        for db_type_name, socket_type_name in _datablock_types_to_write.items():
            input_socket = self.inputs.new(socket_type_name, db_type_name.capitalize())
            input_socket.display_shape = 'SQUARE' # Ensure list sockets are square

    def draw_buttons(self, context, layout):
        # This node has a custom operator button, not the standard activate button
        op = layout.operator("fn.write_file", text="WRITE")
        op.node_id = self.fn_node_id
        # Properties are now inputs, so no need to draw them here directly
        # layout.prop(self, "file_path")
        # layout.prop(self, "overwrite")

    def execute(self, **kwargs):
        # The core logic is in the operator, not here.
        pass