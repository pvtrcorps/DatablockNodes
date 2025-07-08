

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
        tree = kwargs.get('tree')
        
        file_path = kwargs.get(self.inputs['File Path'].identifier)
        reload_flag = kwargs.get(self.inputs['Reload'].identifier)
        link_flag = kwargs.get(self.inputs['Link'].identifier)

        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)

        is_first_run = not map_item or not map_item.datablock_uuids

        if reload_flag or is_first_run:
            if not os.path.exists(file_path):
                print(f"[FN_read_file] Error: File not found at '{file_path}'")
                return {}

            # --- 1. Clean up old datablocks (if not first run) ---
            if not is_first_run:
                print(f"[FN_read_file] Reloading. Cleaning up old datablocks for node {self.name}.")
                old_uuids = map_item.datablock_uuids.split(',')
                for uuid in old_uuids:
                    datablock = uuid_manager.find_datablock_by_uuid(uuid)
                    if datablock:
                        try:
                            # Get the correct bpy.data collection for removal
                            collection_name = type(datablock).__name__.lower() + 's'
                            if hasattr(bpy.data, collection_name):
                                getattr(bpy.data, collection_name).remove(datablock)
                            else:
                                print(f"  - Warning: No direct removal method for type {type(datablock).__name__}")
                        except ReferenceError:
                            print(f"  - Warning: Datablock '{datablock.name}' was already removed (UUID: {uuid}).")
                        except Exception as e:
                            print(f"  - Error removing datablock '{datablock.name}' (UUID: {uuid}): {e}")
            
            # --- 2. Import new datablocks ---
            print(f"[FN_read_file] Reading from '{file_path}' (Link: {link_flag})")
            with bpy.data.libraries.load(file_path, link=link_flag) as (data_from, data_to):\
                # Only load types we are interested in
                for db_type_name in _datablock_types_to_read.keys():
                    if hasattr(data_from, db_type_name):
                        setattr(data_to, db_type_name, getattr(data_from, db_type_name))
            
            # --- 3. Assign UUIDs and update state map ---
            new_uuids = []
            for db_type_name in _datablock_types_to_read.keys():
                if hasattr(data_to, db_type_name):
                    for db in getattr(data_to, db_type_name):
                        uuid_manager.set_uuid(db) # Assign a new UUID
                        new_uuids.append(uuid_manager.get_uuid(db))
            
            if not map_item:
                map_item = tree.fn_state_map.add()
                map_item.node_id = self.fn_node_id
            map_item.datablock_uuids = ",".join(new_uuids)
            
            # --- 4. Reset reload flag (if it was set by the user) ---
            # This is handled by the reconciler's evaluation, as the input socket's value
            # will be passed as 'reload_flag'. We don't modify the socket's default_value here.
            # The user explicitly controls the input socket.

        # --- 5. Return the current datablocks ---
        output = {}
        if map_item and map_item.datablock_uuids:
            all_current_uuids = map_item.datablock_uuids.split(',')
            
            # Categorize and return datablocks for each output socket
            for db_type_name, socket_type_name in _datablock_types_to_read.items():
                # Get the actual datablock type from the socket type name (e.g., FNSocketObjectList -> bpy.types.Object)
                # This is a bit hacky, but works for now. A more robust mapping might be needed.
                # For now, we'll just check if the datablock is an instance of the expected type.
                expected_bpy_type = None
                if 'Object' in socket_type_name: expected_bpy_type = bpy.types.Object
                elif 'Collection' in socket_type_name: expected_bpy_type = bpy.types.Collection
                elif 'Scene' in socket_type_name: expected_bpy_type = bpy.types.Scene
                elif 'Material' in socket_type_name: expected_bpy_type = bpy.types.Material
                elif 'Mesh' in socket_type_name: expected_bpy_type = bpy.types.Mesh
                elif 'Light' in socket_type_name: expected_bpy_type = bpy.types.Light
                elif 'Camera' in socket_type_name: expected_bpy_type = bpy.types.Camera
                elif 'Image' in socket_type_name: expected_bpy_type = bpy.types.Image
                elif 'NodeTree' in socket_type_name: expected_bpy_type = bpy.types.NodeTree
                elif 'Text' in socket_type_name: expected_bpy_type = bpy.types.Text
                elif 'World' in socket_type_name: expected_bpy_type = bpy.types.World
                elif 'WorkSpace' in socket_type_name: expected_bpy_type = bpy.types.WorkSpace
                elif 'String' in socket_type_name: expected_bpy_type = str # Special case for string lists
                elif 'ViewLayer' in socket_type_name: expected_bpy_type = bpy.types.ViewLayer # Special case for view layers

                if expected_bpy_type:
                    current_list = []
                    for uuid_str in all_current_uuids:
                        db = uuid_manager.find_datablock_by_uuid(uuid_str)
                        if db and isinstance(db, expected_bpy_type):
                            current_list.append(db)
                    output[self.outputs[db_type_name.capitalize()].identifier] = current_list
                else:
                    output[self.outputs[db_type_name.capitalize()].identifier] = [] # Empty list if type not handled

        return output
