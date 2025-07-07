"""Manages the persistent UUIDs for Blender datablocks."""

import bpy
import uuid

FN_UUID_PROPERTY = "_fn_uuid"

def get_uuid(datablock):
    """Get the File Nodes UUID for a given datablock."""
    return datablock.get(FN_UUID_PROPERTY, None)

def set_uuid(datablock, target_uuid=None, force_new=False):
    """Assign a new File Nodes UUID to a datablock.
    If target_uuid is provided, it will be used. Otherwise, a new one is generated
    if the datablock doesn't have one already.
    
    """
    if target_uuid:
        datablock[FN_UUID_PROPERTY] = target_uuid
    elif force_new or FN_UUID_PROPERTY not in datablock:
        datablock[FN_UUID_PROPERTY] = str(uuid.uuid4())
    
    
    
    print(f"[UUID_MANAGER] Set UUID {datablock[FN_UUID_PROPERTY]} for '{datablock.name}'")

    return datablock[FN_UUID_PROPERTY]

def find_datablock_by_uuid(uuid_to_find):
    """Scans all relevant bpy.data collections to find a datablock by its UUID."""
    print(f"[UUID_MANAGER] Searching for datablock with UUID: {uuid_to_find}")
    if not uuid_to_find:
        return None
    for collection_name, collection in (('objects', bpy.data.objects), ('scenes', bpy.data.scenes), ('materials', bpy.data.materials), ('meshes', bpy.data.meshes), ('collections', bpy.data.collections), ('cameras', bpy.data.cameras), ('lights', bpy.data.lights), ('images', bpy.data.images), ('node_groups', bpy.data.node_groups), ('texts', bpy.data.texts), ('worlds', bpy.data.worlds)): # Add other relevant collections
        print(f"[UUID_MANAGER] Searching collection: {collection_name}")
        for datablock in collection:
            current_uuid = datablock.get(FN_UUID_PROPERTY, None)
            print(f"[UUID_MANAGER]   Checking datablock: '{datablock.name}' (Type: {type(datablock).__name__}), UUID: {current_uuid}")
            if current_uuid == uuid_to_find:
                print(f"[UUID_MANAGER] Found datablock '{datablock.name}' with matching UUID: {uuid_to_find}")
                return datablock
    print(f"[UUID_MANAGER] Datablock with UUID {uuid_to_find} not found.")
    return None
