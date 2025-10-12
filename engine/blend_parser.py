import bpy
import json
import sys
import argparse
import uuid
import hashlib
from pathlib import Path

# --- V17.1 Refactor: Correct pathing for standalone script execution ---
addon_parent_dir = Path(__file__).resolve().parent.parent.parent
if str(addon_parent_dir) not in sys.path:
    sys.path.append(str(addon_parent_dir))

# Now we can use absolute imports from the package root
from DatablockNodes.scene_assembler import SceneAssembler
from DatablockNodes.engine import utils, constants
from DatablockNodes.proxy_types import RelationshipType, resolve_relationship_type

# V17.7: Define a consistent namespace UUID for the parser
PARSER_NAMESPACE_UUID = uuid.UUID('a8b3c1d2-e4f5-a6b7-c8d9-e0f1a2b3c4d5')

def _promote_pointers_to_relationships(proxy, db_to_proxy_map, all_datablocks):
    """
    Finds ANY property that points to another datablock and promotes it to a
    formal dependency in the `_fn_relationships` dictionary.
    """
    if not isinstance(proxy.properties, dict):
        return

    print(f"[PARSER-DEBUG] Resolving relationships for: {proxy.path}")

    props_to_delete = []

    for key, value in list(proxy.properties.items()):
        if not (isinstance(value, dict) and value.get('_type') in ['NAME_POINTER', 'UUID_POINTER']):
            continue

        target_name = value.get('value')
        target_bl_type = value.get('bl_type')
        if not target_name or not target_bl_type:
            continue

        target_db = all_datablocks.get((target_name, target_bl_type))

        if target_db and target_db in db_to_proxy_map:
            target_proxy = db_to_proxy_map[target_db]
            print(f"[PARSER-DEBUG]  - Found potential relationship: '{key}' -> {target_proxy.path}")
            
            is_ancestor_check = proxy.is_ancestor(target_proxy)
            print(f"[PARSER-DEBUG]  - Checking if '{target_proxy.path}' is ancestor of '{proxy.path}': {is_ancestor_check}")

            if is_ancestor_check:
                print(f"[PARSER-DEBUG]  - Cycle detected. Skipping promotion for key '{key}'. Property will be kept as a pointer.")
                continue
            
            rel_type = resolve_relationship_type(key)
            if not rel_type:
                continue

            print(f"[PARSER-DEBUG]  - Promoting relationship for key '{key}'.")
            proxy.add_relationship(rel_type, target_proxy.fn_uuid)
            props_to_delete.append(key)

    print(f"[PARSER-DEBUG] Properties to delete for {proxy.path}: {props_to_delete}")
    for key in props_to_delete:
        if key in proxy.properties:
            del proxy.properties[key]

def main():
    parser = argparse.ArgumentParser(description="Parse Blender scenes to Datablock Node proxy JSON.")
    parser.add_argument("--output", required=True, help="Output JSON file path.")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

    output_path = Path(args.output)
    current_filepath = bpy.data.filepath
    print(f"[Parser v29] Starting unified parse for: {current_filepath}")

    assembler = SceneAssembler("root")
    db_to_proxy_map = {}
    root_proxy = assembler.get_root_proxy()

    # --- 1. Pre-populate the map with ALL known datablock types ---
    all_datablocks_by_name = {}
    datablock_sources = constants.FN_TYPE_TO_BLENDER_COLLECTION
    for fn_type, coll_name in datablock_sources.items():
        if hasattr(bpy.data, coll_name):
            for db in getattr(bpy.data, coll_name):
                if isinstance(db, bpy.types.Scene) and db == bpy.context.scene:
                    if db not in db_to_proxy_map:
                        db_to_proxy_map[db] = root_proxy
                elif db not in db_to_proxy_map:
                    proxy = assembler.add_proxy(db.name, fn_type)
                    db_to_proxy_map[db] = proxy
                all_datablocks_by_name[(db.name, db.bl_rna.identifier)] = db

    # --- 2. Capture state and resolve all relationships ---
    scene_collections = {s.collection for s in bpy.data.scenes}

    for db, proxy in db_to_proxy_map.items():
        initial_properties = utils.capture_datablock_state(db)
        proxy.properties.update(initial_properties)
        
        _promote_pointers_to_relationships(proxy, db_to_proxy_map, all_datablocks_by_name)

        # --- V18: Explicit Collection Linking for Objects---
        if isinstance(db, bpy.types.Object) and hasattr(db, 'users_collection'):
            added_root = False
            for coll in db.users_collection:
                if coll in scene_collections:
                    if not added_root:
                        proxy.add_relationship(RelationshipType.COLLECTION_LINK, root_proxy.fn_uuid)
                        added_root = True
                elif coll in db_to_proxy_map:
                    coll_proxy = db_to_proxy_map[coll]
                    proxy.add_relationship(RelationshipType.COLLECTION_LINK, coll_proxy.fn_uuid)

        # Set the final source info and deterministic UUID
        source_info = {
            'type': 'file',
            'filepath': current_filepath,
            'datablock_name': db.name,
            'datablock_type': proxy.properties.get('datablock_type')
        }
        proxy.properties['_fn_source'] = source_info
        unique_name = f"{current_filepath}::{db.name}::{source_info.get('datablock_type', '')}"
        proxy.fn_uuid = uuid.uuid5(PARSER_NAMESPACE_UUID, unique_name)

    # --- V18.3: Explicit Collection Linking ---
    # Part A: Links between regular collections
    for parent_coll_db in bpy.data.collections:
        # We are not interested in scene collections as parents here, they are handled in Part B
        if parent_coll_db in scene_collections:
            continue
        if parent_coll_db not in db_to_proxy_map: continue
        parent_proxy = db_to_proxy_map[parent_coll_db]

        for child_coll_db in parent_coll_db.children:
            if not isinstance(child_coll_db, bpy.types.Collection): continue
            if child_coll_db not in db_to_proxy_map: continue
            child_proxy = db_to_proxy_map[child_coll_db]
            
            child_proxy.add_relationship(RelationshipType.COLLECTION_LINK, parent_proxy.fn_uuid)

    # Part B: Links from Scenes to top-level collections
    for scene_db in bpy.data.scenes:
        scene_master_coll = scene_db.collection
        for top_level_coll in scene_master_coll.children:
            if not isinstance(top_level_coll, bpy.types.Collection): continue
            if top_level_coll not in db_to_proxy_map: continue
            child_proxy = db_to_proxy_map[top_level_coll]

            child_proxy.add_relationship(RelationshipType.COLLECTION_LINK, root_proxy.fn_uuid)

    # --- V17.7: Reorder properties for easier debugging ---
    for proxy in root_proxy.get_flat_list():
        if not isinstance(proxy.properties, dict):
            continue
        
        reordered_props = {}
        
        # Move special keys to the top
        if '_fn_source' in proxy.properties:
            reordered_props['_fn_source'] = proxy.properties.pop('_fn_source')
        if '_fn_relationships' in proxy.properties:
            reordered_props['_fn_relationships'] = proxy.properties.pop('_fn_relationships')
            
        # Add the rest of the properties
        reordered_props.update(proxy.properties)
        proxy.properties = reordered_props

    # --- 3. Establish parenting hierarchy (as a final step) ---
    for obj_db, obj_proxy in db_to_proxy_map.items():
        if isinstance(obj_db, bpy.types.Object) and obj_db.parent and obj_db.parent in db_to_proxy_map:
            parent_proxy = db_to_proxy_map[obj_db.parent]
            if obj_proxy.parent != parent_proxy:
                if obj_proxy.parent:
                    obj_proxy.parent.children.remove(obj_proxy)
                obj_proxy.parent = parent_proxy
                parent_proxy.children.append(obj_proxy)
                obj_proxy.path = f"{parent_proxy.path}/{obj_proxy.path.split('/')[-1]}"

    # --- 4. Serialize and write to file ---
    library_dict = root_proxy.to_dict()
    final_output = {
        "metadata": {
            "source_hash": hashlib.sha256(Path(current_filepath).read_bytes()).hexdigest(),
            "blender_filepath": current_filepath,
            "active_scene": bpy.context.scene.name if bpy.context.scene else ""
        },
        "scenes": {},
        "library": library_dict
    }

    with open(output_path, 'w') as f:
        json.dump(final_output, f, indent=2)

    print("[Parser v29] Successfully parsed file.")

if __name__ == "__main__":
    main()