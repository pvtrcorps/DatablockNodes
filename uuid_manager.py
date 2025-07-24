"""Manages the persistent UUIDs for Blender datablocks, with a performance cache."""

import bpy
import uuid
from . import logger

FN_UUID_PROPERTY = "_fn_uuid"

# Module-level cache for O(1) UUID lookups.
# Format: { "uuid_string": datablock }
_UUID_CACHE = {}
_CACHE_POPULATED = False

def _populate_cache():
    """Scans all bpy.data collections to populate the UUID cache."""
    global _UUID_CACHE, _CACHE_POPULATED
    if _CACHE_POPULATED:
        return

    logger.log("[UUID_MANAGER] Cache is cold. Populating...")
    _UUID_CACHE.clear()
    for collection in (bpy.data.objects, bpy.data.scenes, bpy.data.materials, 
                       bpy.data.meshes, bpy.data.collections, bpy.data.cameras, 
                       bpy.data.lights, bpy.data.images, bpy.data.node_groups, 
                       bpy.data.texts, bpy.data.worlds, bpy.data.armatures, 
                       bpy.data.actions):
        for datablock in collection:
            uuid_val = datablock.get(FN_UUID_PROPERTY)
            if uuid_val:
                _UUID_CACHE[uuid_val] = datablock
    _CACHE_POPULATED = True
    logger.log(f"[UUID_MANAGER] Cache populated with {len(_UUID_CACHE)} items.")

def get_uuid(datablock):
    """Get the File Nodes UUID for a given datablock."""
    return datablock.get(FN_UUID_PROPERTY, None)

def register_datablock(datablock, uuid_val):
    """Registers a datablock in the cache."""
    _UUID_CACHE[uuid_val] = datablock

def unregister_datablock(datablock):
    """Removes a datablock from the cache."""
    uuid_val = get_uuid(datablock)
    if uuid_val and uuid_val in _UUID_CACHE:
        del _UUID_CACHE[uuid_val]

def set_uuid(datablock, target_uuid=None, force_new=False):
    """Assign a new File Nodes UUID to a datablock and registers it in the cache."""
    new_uuid = None
    if target_uuid:
        new_uuid = target_uuid
    elif force_new or FN_UUID_PROPERTY not in datablock:
        new_uuid = str(uuid.uuid4())
    
    if new_uuid:
        datablock[FN_UUID_PROPERTY] = new_uuid
        register_datablock(datablock, new_uuid)
        logger.log(f"[UUID_MANAGER] Set UUID {new_uuid} for '{datablock.name}' and cached.")
        return new_uuid
    
    return get_uuid(datablock)

def find_datablock_by_uuid(uuid_to_find):
    """Finds a datablock by its UUID, using the cache for performance."""
    if not uuid_to_find:
        return None

    # Ensure the cache is populated on the first run.
    _populate_cache()

    # O(1) lookup from the cache.
    return _UUID_CACHE.get(uuid_to_find)

def get_all_managed_datablocks():
    """Returns a dictionary of all datablocks managed by the system from the cache."""
    _populate_cache()
    return _UUID_CACHE

def is_managed(datablock):
    """Checks if a datablock has a File Nodes UUID."""
    return FN_UUID_PROPERTY in datablock

def invalidate_cache():
    """Marks the cache as dirty, forcing a repopulation on next access."""
    global _CACHE_POPULATED
    _CACHE_POPULATED = False
    logger.log("[UUID_MANAGER] Cache invalidated.")
