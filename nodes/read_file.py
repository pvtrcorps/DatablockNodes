

import bpy
import os
from .base import FNBaseNode
from .. import uuid_manager
from ..sockets import (
    FNSocketString, FNSocketBool,
    FNSocketSceneList, FNSocketObjectList, FNSocketCollectionList, FNSocketWorldList,
    FNSocketCameraList, FNSocketImageList, FNSocketLightList, FNSocketMaterialList,
    FNSocketMeshList, FNSocketNodeTreeList, FNSocketTextList, FNSocketWorkSpaceList,
    FNSocketStringList, FNSocketViewLayerList
)
from .. import logger

# Define which datablock types the node will handle and their corresponding socket types
_datablock_types_to_read = {
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

class FN_read_file(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_read_file"
    bl_label = "Read File"

    # Node properties (will be converted to inputs)
    # file_path: bpy.props.StringProperty(...)
    # reload: bpy.props.BoolProperty(...)
    # link: bpy.props.BoolProperty(...)

    def init(self, context):
        FNBaseNode.init(self, context)
        
        # Clear existing inputs/outputs to re-add them
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add input sockets
        self.inputs.new('FNSocketString', "File Path").subtype = 'FILE_PATH'
        self.inputs.new('FNSocketBool', "Reload").default_value = False
        self.inputs.new('FNSocketBool', "Link").default_value = False

        # Add output sockets for all supported datablock types
        for db_type_name, socket_type_name in _datablock_types_to_read.items():
            output_socket = self.outputs.new(socket_type_name, db_type_name.capitalize())
            output_socket.display_shape = 'SQUARE' # Ensure list sockets are square

    def draw_buttons(self, context, layout):
        # Properties are now inputs, so no need to draw them here directly
        # layout.prop(self, "file_path")
        # row = layout.row()
        # row.prop(self, "reload")
        # row.prop(self, "link")
        pass

    def execute(self, **kwargs):
        file_path = kwargs.get(self.inputs['File Path'].identifier)
        reload_flag = kwargs.get(self.inputs['Reload'].identifier) # This flag will now primarily influence the hash/re-evaluation
        link_flag = kwargs.get(self.inputs['Link'].identifier)

        if not os.path.exists(file_path):
            logger.log(f"[FN_read_file] Error: File not found at '{file_path}'")
            # Return empty outputs and an empty state declaration
            output = {}
            for db_type_name, socket_type_name in _datablock_types_to_read.items():
                output[self.outputs[db_type_name.capitalize()].identifier] = []
            return {**output, 'states': {self.fn_node_id: ""}}

        # Load new datablocks
        logger.log(f"[FN_read_file] Reading from '{file_path}' (Link: {link_flag})")
        loaded_datablocks = []
        with bpy.data.libraries.load(file_path, link=link_flag) as (data_from, data_to):
            for db_type_name in _datablock_types_to_read.keys():
                if hasattr(data_from, db_type_name):
                    # Load into data_to
                    setattr(data_to, db_type_name, getattr(data_from, db_type_name))
                    # Collect loaded datablocks and ensure they have UUIDs
                    for db in getattr(data_to, db_type_name):
                        uuid_manager.set_uuid(db) # Assign a new UUID if it doesn't have one
                        loaded_datablocks.append(db)

        # Prepare the declarative output
        declarations = {
            'load_file': {
                'file_path': file_path,
                'link_flag': link_flag,
                'datablock_types': list(_datablock_types_to_read.keys())
            }
        }

        output = {}
        for db_type_name, socket_type_name in _datablock_types_to_read.items():
            output[self.outputs[db_type_name.capitalize()].identifier] = [] # Node now outputs empty lists, reconciler will fill

        # Declare the state for this node: it will be filled by the reconciler
        state_id = self.fn_node_id
        output['states'] = {state_id: ""} # State will be updated by reconciler with loaded UUIDs

        return {**output, 'declarations': declarations}
