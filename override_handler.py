import bpy
import json
from . import logger, uuid_manager
from .engine import utils

def _calculate_overrides(initial_state, current_state):
    """Compares two state dictionaries and returns a dict with only the differences."""
    overrides = {}
    all_keys = initial_state.keys() | current_state.keys()
    for key in all_keys:
        initial_value = initial_state.get(key)
        current_value = current_state.get(key)
        if initial_value != current_value:
            overrides[key] = current_value
    return overrides

@bpy.app.handlers.persistent
def depsgraph_update_post_handler(scene, depsgraph):
    # Find the active node tree
    tree = next((nt for nt in bpy.data.node_groups if hasattr(nt, 'bl_idname') and nt.bl_idname == 'DatablockTreeType'), None)
    if not tree:
        return

    # --- Optimization: Iterate only over updated datablocks ---
    for update in depsgraph.updates:
        db = update.id

        # Check if the updated datablock is one we manage
        if not uuid_manager.is_managed(db):
            continue

        # From here, the logic is the same, but it only runs for the specific updated datablock
        uuid_str = uuid_manager.get_uuid(db)
        if not uuid_str:
            continue

        # Find the initial state snapshot for this datablock
        initial_state_entry = next((item for item in tree.fn_initial_state_map if item.datablock_uuid == uuid_str), None)
        if not initial_state_entry:
            continue # No snapshot, so we can't compare it

        try:
            initial_state = json.loads(initial_state_entry.state_data_json)
        except json.JSONDecodeError:
            continue # Corrupted snapshot

        # Get the current, evaluated state of the datablock
        evaluated_db = db.evaluated_get(depsgraph) if hasattr(db, 'evaluated_get') else db
        current_state = utils.capture_initial_state(evaluated_db)

        # Calculate the difference
        overrides = _calculate_overrides(initial_state, current_state)

        if overrides:
            logger.log(f"[OverrideHandler] Detected {len(overrides)} overrides for {db.name} ({uuid_str})")
            # Find or create an override entry
            override_entry = next((item for item in tree.fn_override_map if item.datablock_uuid == uuid_str), None)
            if not override_entry:
                override_entry = tree.fn_override_map.add()
                override_entry.datablock_uuid = uuid_str
            
            # Update the stored overrides
            # If there were previous overrides, merge the new ones on top
            if override_entry.override_data_json:
                try:
                    existing_overrides = json.loads(override_entry.override_data_json)
                    existing_overrides.update(overrides)
                    override_entry.override_data_json = json.dumps(existing_overrides)
                except json.JSONDecodeError:
                    override_entry.override_data_json = json.dumps(overrides)
            else:
                override_entry.override_data_json = json.dumps(overrides)

def register():
    if depsgraph_update_post_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post_handler)
    logger.log("Override handler registered")

def unregister():
    if depsgraph_update_post_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post_handler)
    logger.log("Override handler unregistered")
