import bpy
from .. import uuid_manager

def get_or_create_datablock(node: bpy.types.Node, tree: bpy.types.NodeTree, creation_func: callable, update_func: callable = None):
    """Handles the boilerplate logic for creating, finding, and recreating datablocks.

    This utility function encapsulates the core logic for creator nodes.
    It checks if a node already manages a datablock, finds it in bpy.data,
    recreates it if it's missing, or creates it for the first time.

    Args:
        node: The creator node instance.
        tree: The node tree.
        creation_func: A function that takes no arguments and returns a new datablock.
        update_func: An optional function that takes the existing datablock and updates it.

    Returns:
        The found, recreated, or newly created datablock.
    """
    existing_map_item = next((item for item in tree.fn_state_map if item.node_id == node.fn_node_id), None)
    datablock = None

    if existing_map_item:
        # The node has managed a datablock before.
        found_datablock = uuid_manager.find_datablock_by_uuid(existing_map_item.datablock_uuid)

        if found_datablock:
            # We found the datablock, reuse it.
            datablock = found_datablock
            print(f"  - Reusing existing {type(datablock).__name__}: {datablock.name}")
            # Perform any updates if an update function is provided.
            if update_func:
                update_func(datablock)
        else:
            # The datablock is missing, recreate it with the original UUID.
            print(f"  - Datablock missing. Recreating with UUID {existing_map_item.datablock_uuid}...")
            datablock = creation_func()
            uuid_manager.set_uuid(datablock, existing_map_item.datablock_uuid)
            print(f"  - Recreated {type(datablock).__name__}: {datablock.name}")
    else:
        # This is the first time the node is executed, create a new datablock.
        datablock = creation_func()
        uuid_manager.set_uuid(datablock) # Assign a new UUID
        print(f"  - Created new {type(datablock).__name__}: {datablock.name} (UUID: {uuid_manager.get_uuid(datablock)})")
        
        # Register the new datablock in the state map.
        map_item = tree.fn_state_map.add()
        map_item.node_id = node.fn_node_id
        map_item.datablock_uuid = uuid_manager.get_uuid(datablock)

    return datablock
