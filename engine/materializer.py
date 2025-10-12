import bpy
import json
from collections import defaultdict
from .. import logger, uuid_manager
from ..proxy_types import RelationshipType
from ..properties import _datablock_creation_map
from . import utils, constants

def materialize_plan(plan: list, target_scene: bpy.types.Scene, tree: bpy.types.NodeTree):
    logger.log(f"--- Materializer V15: Processing plan for target scene ''{target_scene.name}'' ---")
    
    # --- Phase 1: Pre-Materialization (Analysis and Grouping) ---
    # logger.log("[Materializer-P0] Starting Pre-Materialization Analysis")
    
    append_map = defaultdict(lambda: defaultdict(list))
    procedural_proxies = []
    uuid_proxy_map = {str(p.fn_uuid): p for p in plan}
    
    for proxy in plan:
        source_info = proxy.properties.get('_fn_source')
        db_type = proxy.properties.get('datablock_type')

        if source_info and source_info.get('type') == 'file':
            if uuid_manager.find_datablock_by_uuid(str(proxy.fn_uuid)):
                continue

            if db_type == 'SCENE':
                continue

            filepath = source_info['filepath']
            db_name = source_info.get('datablock_name')

            if not db_type or not db_name:
                continue

            db_type_plural = constants.FN_TYPE_TO_BLENDER_COLLECTION.get(db_type)
            if not db_type_plural:
                continue
            append_map[filepath][db_type_plural].append(db_name)
        
        elif db_type: # It's a procedural proxy if it has a type but isn't from a file
            procedural_proxies.append(proxy)

    # --- Phase 2: The Append/Create Pass ---
    # logger.log("[Materializer-P1] Starting Append/Create Pass")

    for filepath, categories in append_map.items():
        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            for category, names in categories.items():
                if hasattr(data_to, category):
                    setattr(data_to, category, names)

    for proxy in procedural_proxies:
        if uuid_manager.find_datablock_by_uuid(str(proxy.fn_uuid)):
            continue
        
        db_type = proxy.properties.get('datablock_type')
        db_name = proxy.properties.get('name', 'unnamed')
        creation_func = _datablock_creation_map.get(db_type)
        
        if not creation_func:
            continue

        datablock = None
        if db_type == 'OBJECT':
            object_data = None
            data_relationships = proxy.get_relationships_by_type(RelationshipType.OBJECT_DATA)
            if data_relationships:
                object_data = uuid_manager.find_datablock_by_uuid(data_relationships[0].target_uuid)
            datablock = creation_func(db_name, object_data)
        
        elif db_type == 'LIGHT':
            light_type = proxy.properties.get('type', 'POINT')
            datablock = creation_func(name=db_name, type=light_type)

        else:
            datablock = creation_func(db_name)

        if db_type == 'MESH' and '_fn_geometry_data' in proxy.properties:
            geo_data = proxy.properties['_fn_geometry_data']
            datablock.from_pydata(geo_data.get('vertices', []), geo_data.get('edges', []), geo_data.get('faces', []))
            datablock.update()
        
        if datablock:
            uuid_manager.set_uuid(datablock, str(proxy.fn_uuid))

    for proxy in plan:
        if not proxy.properties.get('datablock_type'): continue
        if uuid_manager.find_datablock_by_uuid(str(proxy.fn_uuid)):
            continue

        source_info = proxy.properties.get('_fn_source', {})
        db_name = source_info.get('datablock_name', proxy.properties.get('name'))
        db_type = source_info.get('datablock_type', proxy.properties.get('datablock_type'))
        
        collection_name = constants.FN_TYPE_TO_BLENDER_COLLECTION.get(db_type)
        collection = getattr(bpy.data, collection_name, None) if collection_name else None
        if collection:
            datablock = collection.get(db_name)
            if datablock:
                uuid_manager.set_uuid(datablock, str(proxy.fn_uuid))

    # --- Phase 3: State Application (Base, Snapshot, and Overrides) ---
    # logger.log("[Materializer-P3] Starting State Application Pass")
    for proxy in plan:
        datablock = uuid_manager.find_datablock_by_uuid(str(proxy.fn_uuid))
        if not datablock:
            continue

        # --- 3a: Apply Base State from Nodes ---
        for key, value in proxy.properties.items():
            if key.startswith('_') or key in ['datablock_type', 'name']:
                continue
            #logger.log(f"[Materializer] Attempting to set property '{key}' to '{value}' on Blender datablock '{datablock.name}' (Type: {datablock.bl_rna.identifier})")
            try:
                utils.set_nested_property(datablock, key, value)
                #logger.log(f"[Materializer] Successfully set property '{key}' on '{datablock.name}'.")
            except Exception as e:
                logger.log(f"[Materializer] Failed to set base property '{key}' on '{datablock.name}': {e}", level='WARNING')

        # --- 3b: Establish Relationships (Parenting and Collections) ---
        # This must happen *before* snapshotting so the relationships are in the initial state.
        if isinstance(datablock, bpy.types.Object):
            # Parenting
            if proxy.parent:
                parent_db = uuid_manager.find_datablock_by_uuid(str(proxy.parent.fn_uuid))
                if parent_db and isinstance(parent_db, bpy.types.Object):
                    if datablock.parent != parent_db:
                        datablock.parent = parent_db

            # Object to Collection Linking
            # First, unlink from all collections this object is currently in
            for coll in datablock.users_collection:
                coll.objects.unlink(datablock)

            # Then, link to the collections specified in the proxy
            for relationship in proxy.get_relationships_by_type(RelationshipType.COLLECTION_LINK):
                target_proxy = uuid_proxy_map.get(relationship.target_uuid)
                target_collection = None

                if target_proxy and target_proxy.path == '/root':
                    target_collection = target_scene.collection
                else:
                    target_db = uuid_manager.find_datablock_by_uuid(relationship.target_uuid)
                    if isinstance(target_db, bpy.types.Scene):
                        target_collection = target_db.collection
                    elif isinstance(target_db, bpy.types.Collection):
                        target_collection = target_db

                if target_collection and datablock.name not in target_collection.objects:
                    target_collection.objects.link(datablock)

            # V17.8: Material Linking
            material_relationships = proxy.get_relationships_by_type(RelationshipType.ACTIVE_MATERIAL)
            if material_relationships:
                material_rel = material_relationships[0]
                material_db = uuid_manager.find_datablock_by_uuid(material_rel.target_uuid)
                material_proxy = uuid_proxy_map.get(material_rel.target_uuid)
                if material_db and isinstance(material_db, bpy.types.Material):
                    if datablock.active_material != material_db:
                        datablock.active_material = material_db
                        logger.log(f"[Materializer] Set active material for '{datablock.name}' to '{material_db.name}'")
                else:
                    target_info = material_proxy.path if material_proxy else material_rel.target_uuid
                    logger.log(
                        f"[Materializer] Could not resolve material relationship target: {target_info}",
                        level='WARNING'
                    )

        elif isinstance(datablock, bpy.types.Collection):
            # Collection to Collection Linking (Hierarchy)
            for relationship in proxy.get_relationships_by_type(RelationshipType.COLLECTION_LINK):
                target_proxy = uuid_proxy_map.get(relationship.target_uuid)
                target_parent_collection = None

                if target_proxy and target_proxy.path == '/root':
                    target_parent_collection = target_scene.collection
                else:
                    parent_db = uuid_manager.find_datablock_by_uuid(relationship.target_uuid)
                    if isinstance(parent_db, bpy.types.Scene):
                        target_parent_collection = parent_db.collection
                    elif isinstance(parent_db, bpy.types.Collection):
                        target_parent_collection = parent_db

                if target_parent_collection and datablock.name not in target_parent_collection.children:
                    target_parent_collection.children.link(datablock)

        elif isinstance(datablock, bpy.types.Scene):
            for rel_type in [RelationshipType.SCENE_CAMERA, RelationshipType.SCENE_WORLD]:
                for relationship in proxy.get_relationships_by_type(rel_type):
                    target_db = uuid_manager.find_datablock_by_uuid(relationship.target_uuid)
                    target_proxy = uuid_proxy_map.get(relationship.target_uuid)
                    attr_name = rel_type.value

                    if not target_db:
                        target_info = target_proxy.path if target_proxy else relationship.target_uuid
                        logger.log(
                            f"[Materializer] Could not find target datablock for scene relationship: {target_info}",
                            level='WARNING'
                        )
                        continue

                    try:
                        setattr(datablock, attr_name, target_db)
                        logger.log(f"[Materializer] Set scene relationship: {datablock.name}.{attr_name} -> {target_db.name}")
                    except Exception as e:
                        logger.log(
                            f"[Materializer] Failed to set scene relationship '{attr_name}' on '{datablock.name}': {e}",
                            level='WARNING'
                        )

        # --- 3c: Snapshot the Initial State ---
        # This "photo" is taken *after* the node-defined state and relationships are applied,
        # but *before* any user overrides are applied.
        try:
            initial_state = utils.capture_datablock_state(datablock)
            snapshot_entry = tree.fn_initial_state_map.add()
            snapshot_entry.datablock_uuid = str(proxy.fn_uuid)
            snapshot_entry.state_data_json = json.dumps(initial_state)
        except Exception as e:
            logger.log(f"[Materializer] Failed to snapshot state for '{datablock.name}': {e}", level='ERROR')

        # --- 3d: Apply Persistent User Overrides ---
        override_entry = next((item for item in tree.fn_override_map if item.datablock_uuid == str(proxy.fn_uuid)), None)
        if override_entry and override_entry.override_data_json:
            try:
                overrides = json.loads(override_entry.override_data_json)
                logger.log(f"[Materializer] Applying {len(overrides)} overrides to '{datablock.name}'")
                for key, value in overrides.items():
                    try:
                        utils.set_nested_property(datablock, key, value)
                    except Exception as e:
                        logger.log(f"[Materializer] Failed to apply override property '{key}' on '{datablock.name}': {e}", level='WARNING')
            except json.JSONDecodeError:
                logger.log(f"[Materializer] Could not decode overrides for '{datablock.name}'. Skipping.", level='WARNING')