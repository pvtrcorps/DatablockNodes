"""Manages the persistent UUIDs for Blender datablocks."""

import bpy
import uuid
import time

FN_UUID_PROPERTY = "_fn_uuid"

def get_uuid(datablock):
    """Get the File Nodes UUID for a given datablock."""
    return datablock.get(FN_UUID_PROPERTY, None)

def set_uuid(datablock, target_uuid=None, force_new=False):
    """Assign a new File Nodes UUID to a datablock.
    If target_uuid is provided, it will be used. Otherwise, a new one is generated
    if the datablock's doesn't have one already.
    
    """
    if target_uuid:
        datablock[FN_UUID_PROPERTY] = target_uuid
    elif force_new or FN_UUID_PROPERTY not in datablock:
        datablock[FN_UUID_PROPERTY] = str(uuid.uuid4())
    
    
    
    print(f"[UUID_MANAGER] Set UUID {datablock[FN_UUID_PROPERTY]} for '{datablock.name}'")

    return datablock[FN_UUID_PROPERTY]

def find_datablock_by_uuid(uuid_to_find):
    """Scans all relevant bpy.data collections to find a datablock by its UUID."""
    if not uuid_to_find:
        return None

    # With the two-phase reconciler, we can now expect the datablock to exist
    # in a single, robust search without retries.
    for collection in (bpy.data.objects, bpy.data.scenes, bpy.data.materials, 
                       bpy.data.meshes, bpy.data.collections, bpy.data.cameras, 
                       bpy.data.lights, bpy.data.images, bpy.data.node_groups, 
                       bpy.data.texts, bpy.data.worlds, bpy.data.armatures, 
                       bpy.data.actions):
        for datablock in collection:
            if datablock.get(FN_UUID_PROPERTY) == uuid_to_find:
                return datablock
    
    return None


def get_or_create_uuid(datablock):
    """Get the UUID if it exists, otherwise create a new one."""
    uuid = get_uuid(datablock)
    if uuid is None:
        uuid = set_uuid(datablock)
    return uuid

def generate_uuid():
    """Generates a new UUID string."""
    return str(uuid.uuid4())

def is_valid_uuid(uuid_string):
    """Checks if a string is a valid UUID."""
    if not isinstance(uuid_string, str):
        return False
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

def get_all_managed_datablocks():
    """Returns a dictionary of all datablocks managed by the system, keyed by their UUID."""
    managed_dbs = {}
    for collection in (bpy.data.objects, bpy.data.scenes, bpy.data.materials, bpy.data.meshes, bpy.data.collections, bpy.data.cameras, bpy.data.lights, bpy.data.images, bpy.data.node_groups, bpy.data.texts, bpy.data.worlds, bpy.data.armatures, bpy.data.actions):
        for db in collection:
            uuid = db.get(FN_UUID_PROPERTY)
            if uuid:
                managed_dbs[uuid] = db
    return managed_dbs