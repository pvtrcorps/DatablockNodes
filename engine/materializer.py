import bpy
import json
from .. import logger, uuid_manager
from ..properties import _datablock_creation_map
from . import utils

def materialize_plan(plan: list, tree: bpy.types.NodeTree):
    """
    Materializes the scene graph from a dependency-sorted plan.
    This process now includes applying base properties, saving an initial state snapshot,
    and applying any user overrides.
    """
    logger.log("--- Materializer V11: Processing dependency-sorted plan ---")
    
    # --- Pass 1: Creation ---
    logger.log("[Materializer-P1] Starting Creation Pass")
    for proxy in plan:
        if uuid_manager.find_datablock_by_uuid(str(proxy.fn_uuid)):
            logger.log(f"[Materializer-P1] Skipping existing datablock for {proxy.path}")
            continue

        db_type = proxy.properties.get('datablock_type')
        db_name = proxy.properties.get('name', 'unnamed')
        datablock = None

        logger.log(f"[Materializer-P1] Attempting to create {db_type} for path {proxy.path}")

        try:
            if db_type == 'OBJECT':
                object_data = None
                if '_fn_relationships' in proxy.properties and 'data' in proxy.properties['_fn_relationships']:
                    data_path = proxy.properties['_fn_relationships']['data']
                    logger.log(f"[Materializer-P1] Object {proxy.path} requires data from {data_path}")
                    # Find the proxy for the data
                    data_proxy = next((p for p in plan if p.path == data_path), None)
                    if data_proxy:
                        # Find the already-materialized datablock for that proxy
                        object_data = uuid_manager.find_datablock_by_uuid(str(data_proxy.fn_uuid))
                        if object_data:
                            logger.log(f"[Materializer-P1] Found materialized data '{object_data.name}' for object {proxy.path}")
                        else:
                            logger.log(f"[Materializer-P1] ERROR: Data proxy {data_path} was found, but its datablock is not materialized yet. Check dependency sorting.")
                    else:
                        logger.log(f"[Materializer-P1] ERROR: Data path {data_path} not found in plan for object {proxy.path}")
                
                datablock = bpy.data.objects.new(db_name, object_data)
            else:
                creation_func = _datablock_creation_map.get(db_type)
                if not creation_func:
                    logger.log(f"[Materializer-P1] No creation function for type '{db_type}'")
                    continue
                
                creation_args = {'name': db_name}
                if db_type == 'LIGHT':
                    creation_args['type'] = proxy.properties.get('type', 'POINT')
                
                datablock = creation_func(**creation_args)

            if datablock:
                uuid_manager.set_uuid(datablock, str(proxy.fn_uuid))
                logger.log(f"[Materializer-P1] CREATED {db_type}: {datablock.name} (UUID: {proxy.fn_uuid})")

        except Exception as e:
            logger.log(f"[Materializer-P1] FAILED to create {db_type} for {proxy.path}: {e}")

    # --- Pass 2: Configuration, Snapshot, and Overrides ---
    logger.log("[Materializer-P2] Starting Configuration, Snapshot, and Overrides Pass")
    for proxy in plan:
        datablock = uuid_manager.find_datablock_by_uuid(str(proxy.fn_uuid))
        if not datablock:
            continue

        # logger.log(f"[Materializer-P2] Configuring base state for {proxy.path}")
        for key, value in proxy.properties.items():
            if key.startswith('_') or key in ['datablock_type']:
                continue
            
            try:
                utils.set_nested_property(datablock, key, value)
            except Exception as e:
                logger.log(f"[Materializer-P2] Could not set base property '{key}' on {datablock.name}: {e}")

        uuid_str = str(proxy.fn_uuid)
        initial_state_entry = next((item for item in tree.fn_initial_state_map if item.datablock_uuid == uuid_str), None)
        if not initial_state_entry:
            # logger.log(f"[Materializer-P2] Capturing initial state for {datablock.name} ({uuid_str})")
            initial_state = utils.capture_initial_state(datablock)
            new_entry = tree.fn_initial_state_map.add()
            new_entry.datablock_uuid = uuid_str
            new_entry.state_data_json = json.dumps(initial_state)

        override_entry = next((item for item in tree.fn_override_map if item.datablock_uuid == uuid_str), None)
        if override_entry and override_entry.override_data_json:
            # logger.log(f"[Materializer-P2] Applying overrides for {datablock.name} ({uuid_str})")
            try:
                overrides = json.loads(override_entry.override_data_json)
                for key, value in overrides.items():
                    final_value = utils.from_json_safe(value)
                    utils.set_nested_property(datablock, key, final_value)
            except json.JSONDecodeError:
                logger.log(f"[Materializer-P2] ERROR: Could not decode override JSON for {uuid_str}")
            except Exception as e:
                logger.log(f"[Materializer-P2] ERROR: Failed to apply override for {uuid_str}: {e}")

    # --- Pass 3: Relationships (Parenting and Linking) ---
    logger.log("[Materializer-P3] Starting Relationship Pass")
    proxy_map = {p.path: p for p in plan} # Create a map for quick path lookups

    for proxy in plan:
        from_db = uuid_manager.find_datablock_by_uuid(str(proxy.fn_uuid))
        if not from_db or not isinstance(from_db, bpy.types.Object):
            # Parenting logic only applies to Objects.
            continue

        # --- 1. Infer Parenting from Path Hierarchy ---
        if '/' in proxy.path.lstrip('/'): # Check if it's not a root-level proxy
            parent_path = '/' + '/'.join(proxy.path.lstrip('/').split('/')[:-1])
            if parent_path in proxy_map:
                parent_proxy = proxy_map[parent_path]
                parent_db = uuid_manager.find_datablock_by_uuid(str(parent_proxy.fn_uuid))
                if parent_db and from_db.parent != parent_db:
                    if isinstance(from_db, bpy.types.Object) and isinstance(parent_db, bpy.types.Object):
                        logger.log(f"[Materializer-P3] Setting parent for '{from_db.name}' to '{parent_db.name}' based on path hierarchy.")
                        from_db.parent = parent_db
                    else:
                        logger.log(f"[Materializer-P3] WARNING: Cannot parent {type(from_db)} to {type(parent_db)}.")

        # --- 2. Process Other Explicit Relationships (like collection linking) ---
        if '_fn_relationships' in proxy.properties:
            for rel_type, target_value in proxy.properties['_fn_relationships'].items():
                if rel_type == 'data': # Data relationship is handled in Pass 1
                    continue
                
                try:
                    if rel_type == 'collection_links':
                        target_paths = target_value if isinstance(target_value, list) else [target_value]
                        for single_target_path in target_paths:
                            target_proxy = proxy_map.get(single_target_path)
                            if not target_proxy:
                                logger.log(f"[Materializer-P3] Could not find target proxy for collection link path: {single_target_path}")
                                continue
                            
                            target_datablock = uuid_manager.find_datablock_by_uuid(str(target_proxy.fn_uuid))
                            if not target_datablock:
                                logger.log(f"[Materializer-P3] Could not find target datablock for collection link path: {single_target_path}")
                                continue

                            collection_to_link_into = target_datablock
                            if isinstance(target_datablock, bpy.types.Scene):
                                collection_to_link_into = target_datablock.collection
                            
                            if not isinstance(collection_to_link_into, bpy.types.Collection):
                                logger.log(f"[Materializer-P3] ERROR: Final target '{collection_to_link_into.name}' is not a collection. Aborting link.")
                                continue

                            if isinstance(from_db, bpy.types.Object) and from_db.name not in collection_to_link_into.objects:
                                collection_to_link_into.objects.link(from_db)
                                logger.log(f"[Materializer-P3] SUCCESS: Linked '{from_db.name}' to collection '{collection_to_link_into.name}'")
                            elif isinstance(from_db, bpy.types.Collection) and from_db.name not in collection_to_link_into.children:
                                collection_to_link_into.children.link(from_db)
                                logger.log(f"[Materializer-P3] SUCCESS: Linked collection '{from_db.name}' to collection '{collection_to_link_into.name}'")
                except Exception as e:
                    logger.log(f"[Materializer-P3] FAILED to process '{rel_type}' for '{proxy.path}': {e}")