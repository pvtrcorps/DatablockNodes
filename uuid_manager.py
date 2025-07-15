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

def find_datablock_by_uuid(uuid_to_find, retries=5, delay=0.01):
    """Scans all relevant bpy.data collections to find a datablock by its UUID, with retries."""
    print(f"[UUID_MANAGER] Searching for datablock with UUID: {uuid_to_find}")
    if not uuid_to_find:
        return None

    for attempt in range(retries):
        for collection_name, collection in (('objects', bpy.data.objects), ('scenes', bpy.data.scenes), ('materials', bpy.data.materials), ('meshes', bpy.data.meshes), ('collections', bpy.data.collections), ('cameras', bpy.data.cameras), ('lights', bpy.data.lights), ('images', bpy.data.images), ('node_groups', bpy.data.node_groups), ('texts', bpy.data.texts), ('worlds', bpy.data.worlds), ('armatures', bpy.data.armatures), ('actions', bpy.data.actions)):
            # print(f"[UUID_MANAGER]   Checking collection: {collection_name}") # Too verbose
            for datablock in collection:
                current_uuid = datablock.get(FN_UUID_PROPERTY, None)
                # print(f"[UUID_MANAGER]     Checking datablock: '{datablock.name}' (Type: {type(datablock).__name__}), UUID: {current_uuid}") # Too verbose
                if current_uuid == uuid_to_find:
                    print(f"[UUID_MANAGER] Found datablock '{datablock.name}' with matching UUID: {uuid_to_find} on attempt {attempt + 1}")
                    return datablock
        
        if attempt < retries - 1:
            print(f"[UUID_MANAGER] Datablock with UUID {uuid_to_find} not found on attempt {attempt + 1}. Retrying in {delay}s...")
            time.sleep(delay)
            # Force a Blender update to give it a chance to register the datablock
            bpy.context.view_layer.update() # This might be the key!
    
    print(f"[UUID_MANAGER] Datablock with UUID {uuid_to_find} not found after {retries} attempts.")
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