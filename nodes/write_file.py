import bpy
from .base import FNBaseNode
from ..sockets import (
    FNSocketString, FNSocketBool, FNSocketPulse,
    FNSocketSceneList, FNSocketObjectList, FNSocketCollectionList, FNSocketWorldList,
    FNSocketCameraList, FNSocketImageList, FNSocketLightList, FNSocketMaterialList,
    FNSocketMeshList, FNSocketNodeTreeList, FNSocketTextList, FNSocketWorkSpaceList,
    FNSocketStringList, FNSocketViewLayerList
)
from .constants import DATABLOCK_TYPES

# Define which datablock types the node will handle and their corresponding socket types
_datablock_types_to_write = {
    item[0].lower() + 's': f"FNSocket{item[0].capitalize()}List" for item in DATABLOCK_TYPES
}


class FN_write_file(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_write_file"
    bl_label = "Write File"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.manages_scene_datablock = True # This node performs an action, it doesn't define a scene state

        # Clear existing inputs/outputs to re-add them
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add input sockets for file path and options
        self.inputs.new('FNSocketString', "File Path").subtype = 'FILE_PATH'
        self.inputs.new('FNSocketBool', "Overwrite").default_value = True

        # Add input sockets for all supported datablock types
        for db_type_name, socket_type_name in _datablock_types_to_write.items():
            input_socket = self.inputs.new(socket_type_name, db_type_name.capitalize())
            input_socket.display_shape = 'SQUARE' # Ensure list sockets are square
        
        self.outputs.new('FNSocketPulse', "Execute")

    def draw_buttons(self, context, layout):
        pass

    def execute(self, **kwargs):
        file_path = kwargs.get(self.inputs['File Path'].identifier)
        overwrite = kwargs.get(self.inputs['Overwrite'].identifier)

        if not file_path:
            return {}

        datablock_uuids_to_write = set()
        for db_type_name in _datablock_types_to_write.keys():
            socket_name = db_type_name.capitalize()
            if socket_name in self.inputs:
                db_input = kwargs.get(self.inputs[socket_name].identifier)
                if db_input:
                    # Ensure we handle both single items and lists gracefully
                    if not isinstance(db_input, list):
                        db_input = [db_input]
                    
                    for db_uuid in db_input:
                        if db_uuid:
                            datablock_uuids_to_write.add(db_uuid)

        return {
            self.outputs[0].identifier: True,
            'declarations': {
                'write_file': {
                    'file_path': file_path,
                    'overwrite': overwrite,
                    'datablock_uuids': list(datablock_uuids_to_write)
                }
            }
        }

def register():
    bpy.utils.register_class(FN_write_file)

def unregister():
    bpy.utils.unregister_class(FN_write_file)
