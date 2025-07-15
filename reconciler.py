import bpy
import hashlib
import json
import mathutils
from bpy.types import bpy_prop_array
from bpy.app.handlers import persistent
from . import uuid_manager
from .properties import _datablock_creation_map
from . import logger

_timer_func = None
_is_executing = False

def _set_nested_property(base, path, value):
    try:
        parts = path.split('.')
        obj = base
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
        return True
    except (AttributeError, TypeError) as e:
        logger.log(f"[FN_ERROR] Could not set nested property '{path}' on {base.name}: {e}")
        return False

def _get_nested_property(base, path):
    try:
        parts = path.split('.')
        obj = base
        for part in parts:
            obj = getattr(obj, part)
        return obj
    except (AttributeError, TypeError):
        return None

@persistent
def datablock_nodes_depsgraph_handler(scene, depsgraph):
    logger.log("--- [FN] Depsgraph Handler Triggered ---")
    global _timer_func, _is_executing


    if _is_executing:
        logger.log("[FN_DEBUG] Execution in progress. Re-entry blocked.")
        return

    active_tree = next((tree for tree in bpy.data.node_groups if hasattr(tree, 'bl_idname') and tree.bl_idname == 'DatablockTreeType' and any(sock.is_final_active for node in tree.nodes for sock in node.outputs)), None)

    if not active_tree:
        return

    def execution_wrapper():
        global _timer_func, _is_executing
        logger.log("[FN_DEBUG] LOCKING execution engine.")
        _is_executing = True
        try:
            trigger_execution(active_tree)
            logger.log("[FN_DEBUG] Execution finished successfully.")
        except Exception as e:
            logger.log(f"[FN_ERROR] An exception occurred during execution: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.log("[FN_DEBUG] UNLOCKING execution engine.")
            _is_executing = False
            _timer_func = None
        return None

    if _timer_func and bpy.app.timers.is_registered(_timer_func):
        bpy.app.timers.unregister(_timer_func)
    
    _timer_func = execution_wrapper
    bpy.app.timers.register(_timer_func, first_interval=0.01)

def trigger_execution(tree: bpy.types.NodeTree):
    logger.log(f"--- Triggering execution for tree '{tree.name}' ---")
    """
    Triggers an evaluation of the active branch, builds an active plan, and
    synchronizes the state in Blender by destroying inactive datablocks and
    creating/updating active ones.
    """
    # 1. Identify the active socket. If none, do nothing.
    active_socket = next((sock for node in tree.nodes for sock in node.outputs if sock.is_final_active), None)
    if not active_socket:
        return

    # 2. Get the nodes involved in the active branch.
    active_branch_nodes = _get_active_branch_node_ids(active_socket)
    logger.log(f"[FN_DEBUG] Active branch nodes: {active_branch_nodes}")

    # 3. Evaluate the active branch to get the execution plan.
    logger.log("[FN_DEBUG] Evaluating active branch...")
    session_cache, active_uuids, active_states, active_relationships, active_assignments, creation_declarations, load_file_declarations = _evaluate_active_branch(tree, active_socket, active_branch_nodes)
    logger.log(f"[FN_DEBUG] Active plan built. UUIDs: {active_uuids}")

    # Process LOAD_FILE declarations before synchronization
    for decl in load_file_declarations:
        file_path = decl['file_path']
        link_flag = decl['link_flag']
        datablock_types = decl['datablock_types']
        node_id = decl['node_id']

        if not os.path.exists(file_path):
            logger.log(f"[FN_read_file] Error: File not found at '{file_path}'")
            continue

        loaded_uuids = []
        with bpy.data.libraries.load(file_path, link=link_flag) as (data_from, data_to):
            for db_type_name in datablock_types:
                if hasattr(data_from, db_type_name):
                    setattr(data_to, db_type_name, getattr(data_from, db_type_name))
                    for db in getattr(data_to, db_type_name):
                        uuid_manager.set_uuid(db) # Assign a new UUID if it doesn't have one
                        loaded_uuids.append(uuid_manager.get_uuid(db))
        
        # Add loaded UUIDs to active_uuids
        active_uuids.update(loaded_uuids)

        # Update the state for the node that declared this load operation
        map_item = next((item for item in tree.fn_state_map if item.node_id == node_id), None)
        if not map_item:
            map_item = tree.fn_state_map.add()
            map_item.node_id = node_id
        map_item.datablock_uuids = ",".join(loaded_uuids)
        logger.log(f"[FN_DEBUG] _synchronize_blender_state: Loaded datablocks from {file_path}. UUIDs: {loaded_uuids}")

    # Force a Blender update to ensure newly created datablocks are registered
    bpy.context.view_layer.update()

    # 4. Synchronize Blender's state with the active plan.
    _synchronize_blender_state(tree, active_uuids, active_states, active_relationships, active_assignments, creation_declarations)

    # 5. Update UI to highlight the active path.
    update_ui_for_active_socket(tree, active_socket, session_cache)


def _serialize_overrides(datablock) -> str:
    """
    Serializes the user-modified properties of a datablock to a JSON string.
    Compares current values against Blender's default values using a JSON-safe conversion.
    """
    if not datablock or not hasattr(datablock, 'bl_rna'):
        return "{}"

    def _to_json_safe(value):
        """Recursively converts complex Blender types to JSON-serializable formats."""
        # 1. Basic Python types
        if isinstance(value, (int, float, str, bool, type(None))):
            return value

        # 2. Mathutils types (Vector, Matrix, Color, Euler, Quaternion)
        # Convert to list, then recursively process elements
        if isinstance(value, (mathutils.Vector, mathutils.Color, mathutils.Euler, mathutils.Quaternion)):
            return list(value) # These are already flat lists of numbers
        if isinstance(value, mathutils.Matrix):
            # A Matrix converts to a list of Vectors. We need to convert each Vector.
            return [_to_json_safe(row) for row in value] # Recursively call for each row (Vector)

        # 3. bpy_prop_array and other iterable bpy_structs
        # Convert to list, then recursively process elements
        if isinstance(value, bpy_prop_array) or (isinstance(value, bpy.types.bpy_struct) and hasattr(value, '__iter__')):
            return [_to_json_safe(item) for item in value] # Recursively call for each item

        # 4. Blender ID types (datablocks)
        if isinstance(value, bpy.types.ID):
            return uuid_manager.get_uuid(value)

        # 5. Generic Python iterables (lists, tuples, sets, frozensets)
        # Recursively convert their elements
        if isinstance(value, (list, tuple, set, frozenset)):
            return [_to_json_safe(item) for item in value]
        
        # 6. Fallback: If we reach here, it's an unhandled type.
        # This should ideally not happen for data we intend to serialize.
        logger.log(f"[FN_WARNING] _to_json_safe: Unhandled type for JSON serialization: {type(value).__name__} ({value}). Omitting property.")
        return None # Omit the property from serialization

    overrides = {}
    rna_properties = datablock.bl_rna.properties

    for prop in rna_properties:
        if prop.is_readonly or prop.is_hidden or prop.type == 'FUNCTION':
            continue
        
        # Skip internal collection properties
        if prop.type == 'COLLECTION' and hasattr(prop, 'srna') and prop.srna and prop.srna.bl_idname == 'bpy_prop_collection_idprop_group':
            continue

        # Skip matrix properties as they are derived and not directly user-editable for overrides
        if prop.identifier in ['matrix_world', 'matrix_local', 'matrix_basis', 'matrix_parent_inverse']:
            continue

        try:
            current_value = _get_nested_property(datablock, prop.identifier)
            if current_value is None: continue

            # Get default value, handling arrays correctly
            default_value = prop.default_array if prop.is_array else prop.default

            # Convert both to a comparable, JSON-safe format
            safe_current = _to_json_safe(current_value)
            if safe_current is None:
                continue
            safe_default = _to_json_safe(default_value)
            if safe_default is None:
                # If default cannot be serialized, we can't compare, so skip this property
                continue

            # If they are the same after conversion, skip
            if safe_current == safe_default:
                continue
            
            # Special handling for pointer properties to store them in our desired format
            if prop.type == 'POINTER' and isinstance(current_value, bpy.types.ID):
                pointed_uuid = uuid_manager.get_uuid(current_value)
                if pointed_uuid:
                    overrides[prop.identifier] = {'_type': 'UUID_POINTER', 'value': pointed_uuid}
                else:
                    overrides[prop.identifier] = None # Pointer is cleared
            else:
                overrides[prop.identifier] = safe_current

        except AttributeError:
            continue

    logger.log(f"[FN_DEBUG] _serialize_overrides for {datablock.name} ({uuid_manager.get_uuid(datablock)}): {overrides}")
    return json.dumps(overrides) if overrides else "{}"

def _apply_overrides(datablock, tree, datablock_uuid):
    """
    Applies stored overrides from the tree's fn_override_map to a datablock.
    """
    override_entry = next((item for item in tree.fn_override_map if item.datablock_uuid == datablock_uuid), None)
    if not override_entry:
        return

    try:
        overrides = json.loads(override_entry.override_data_json)
        logger.log(f"[FN_DEBUG] Applying overrides for {datablock.name} ({datablock_uuid}): {overrides}")
    except json.JSONDecodeError:
        logger.log(f"[FN_ERROR] Could not decode override JSON for {datablock_uuid}")
        return

    for key, value in overrides.items():
        try:
            # Handle UUID pointers
            if isinstance(value, dict) and value.get('_type') == 'UUID_POINTER':
                pointed_db = uuid_manager.find_datablock_by_uuid(value['value'])
                if pointed_db:
                    _set_nested_property(datablock, key, pointed_db)
            # Handle mathutils types stored as lists
            elif isinstance(value, list):
                # Create a new mathutils object from the list
                # We need to know the type of the property to reconstruct it correctly
                prop = _get_nested_property(datablock, key)
                if prop:
                    if isinstance(prop, mathutils.Color):
                        _set_nested_property(datablock, key, mathutils.Color(value))
                    elif isinstance(prop, mathutils.Euler):
                        _set_nested_property(datablock, key, mathutils.Euler(value))
                    elif isinstance(prop, mathutils.Quaternion):
                        _set_nested_property(datablock, key, mathutils.Quaternion(value))
                    else: # Default to Vector for other lists
                        _set_nested_property(datablock, key, mathutils.Vector(value))
            # Handle simple values
            else:
                _set_nested_property(datablock, key, value)
        except (AttributeError, TypeError, ValueError) as e:
            logger.log(f"[FN_WARNING] Could not apply override for property '{key}' on {datablock.name}: {e}")


def _evaluate_active_branch(tree: bpy.types.NodeTree, active_socket: bpy.types.NodeSocket, active_branch_nodes: set):
    """Evaluates only the nodes in the active branch and returns the execution plan for that branch."""
    session_cache = {}
    active_uuids = set()
    active_states = {}
    active_relationships = []
    active_assignments = []
    creation_declarations = {}
    load_file_declarations = [] # New: Collects load file intents

    # We start the recursive evaluation from the final active node.
    # The recursive function `_evaluate_node` will handle the dependency chain.
    _evaluate_node(tree, active_socket.node, session_cache, active_uuids, active_relationships, active_states, active_assignments, creation_declarations, load_file_declarations)

    return session_cache, active_uuids, active_states, active_relationships, active_assignments, creation_declarations, load_file_declarations


def _synchronize_blender_state(tree, active_uuids, active_states, active_relationships, active_assignments, creation_declarations):
    logger.log("--- Synchronizing Blender State ---")
    logger.log(f"Active UUIDs in plan: {active_uuids}")
    """
    Takes the active plan and synchronizes Blender's state.
    Destroys datablocks not in the active plan and creates/updates those that are.
    """
    # --- 1. Destruction Phase ---
    all_managed_datablocks = uuid_manager.get_all_managed_datablocks()
    uuids_to_destroy = set(all_managed_datablocks.keys()) - active_uuids
    logger.log(f"UUIDs to DESTROY: {uuids_to_destroy}")

    if uuids_to_destroy:
        for uuid_to_destroy in uuids_to_destroy:
            datablock_to_destroy = all_managed_datablocks.get(uuid_to_destroy)
            if not datablock_to_destroy:
                continue

            # a. Serialize overrides before destruction
            logger.log(f"[FN_DEBUG] Serializing overrides for {datablock_to_destroy.name} ({uuid_to_destroy})")
            override_json = _serialize_overrides(datablock_to_destroy)
            if override_json and override_json != "{}":
                override_entry = next((item for item in tree.fn_override_map if item.datablock_uuid == uuid_to_destroy), None)
                if not override_entry:
                    override_entry = tree.fn_override_map.add()
                    override_entry.datablock_uuid = uuid_to_destroy
                override_entry.datablock_type = datablock_to_destroy.bl_rna.identifier
                override_entry.override_data_json = override_json

            # b. Remove from Blender
            datablock_type_name = datablock_to_destroy.bl_rna.identifier
            collection = getattr(bpy.data, datablock_type_name.lower() + 's', None)
            if collection:
                try:
                    logger.log(f"[FN_DEBUG] Removing datablock {datablock_to_destroy.name} ({uuid_to_destroy}) from Blender.")
                    collection.remove(datablock_to_destroy)
                except (ReferenceError, RuntimeError) as e:
                    logger.log(f"[FN_WARNING] Could not remove datablock {uuid_to_destroy}: {e}")
    
    # --- 2. Clean up persistent maps from destroyed datablocks ---
    all_managed_uuids = set(uuid_manager.get_all_managed_datablocks().keys())
    
    # Clean state map
    indices_to_remove = [i for i, item in enumerate(tree.fn_state_map) for uuid in item.datablock_uuids.split(',') if uuid and uuid not in all_managed_uuids]
    if indices_to_remove:
        for i in sorted(list(set(indices_to_remove)), reverse=True):
            tree.fn_state_map.remove(i)

    # Clean relationship map
    indices_to_remove = [i for i, item in enumerate(tree.fn_relationships_map) if item.source_uuid not in all_managed_uuids or item.target_uuid not in all_managed_uuids]
    if indices_to_remove:
        for i in sorted(list(set(indices_to_remove)), reverse=True):
            tree.fn_relationships_map.remove(i)

    # Clean property assignments map
    indices_to_remove = [i for i, item in enumerate(tree.fn_property_assignments_map) if item.target_uuid not in all_managed_uuids]
    if indices_to_remove:
        for i in sorted(list(set(indices_to_remove)), reverse=True):
            tree.fn_property_assignments_map.remove(i)

    # Clean override map
    

    # --- 3. Creation/Update Phase ---
    sorted_creation_uuids = _topological_sort_creation_declarations(creation_declarations)
    logger.log(f"[FN_DEBUG] Creation order: {sorted_creation_uuids}")

    for uuid in sorted_creation_uuids:
        if uuid not in active_uuids:
            continue

        datablock = uuid_manager.find_datablock_by_uuid(uuid)
        if not datablock:
            creation_declaration = creation_declarations.get(uuid)
            if creation_declaration:
                logger.log(f"[FN_DEBUG] Creating datablock {uuid} with declaration: {creation_declaration}")
                if creation_declaration['type'] == 'DERIVE':
                    source_uuid = creation_declaration['source_uuid']
                    new_name = creation_declaration['new_name']
                    source_datablock = uuid_manager.find_datablock_by_uuid(source_uuid)

                    if source_datablock:
                        datablock = source_datablock.copy()
                        uuid_manager.set_uuid(datablock, target_uuid=uuid)
                        if new_name:
                            datablock.name = new_name
                        if isinstance(datablock, bpy.types.Scene):
                            datablock.use_extra_user = True
                    else:
                        logger.log(f"[FN_WARNING] Source datablock {source_uuid} not found for derivation of {uuid}.")
                        continue
                elif creation_declaration['type'] == 'COPY':
                    source_uuid = creation_declaration['source_uuid']
                    source_datablock = uuid_manager.find_datablock_by_uuid(source_uuid)

                    if source_datablock:
                        datablock = source_datablock.copy()
                        uuid_manager.set_uuid(datablock, target_uuid=uuid)
                        original_override_entry = next((item for item in tree.fn_override_map if item.datablock_uuid == source_uuid), None)
                        if original_override_entry:
                            new_override_entry = tree.fn_override_map.add()
                            new_override_entry.datablock_uuid = uuid
                            new_override_entry.datablock_type = original_override_entry.datablock_type
                            new_override_entry.override_data_json = original_override_entry.override_data_json
                    else:
                        logger.log(f"[FN_WARNING] Source datablock {source_uuid} not found for copy of {uuid}.")
                        continue
                else:
                    datablock_type = creation_declaration['type']
                    creation_func = _datablock_creation_map.get(datablock_type)

                    if creation_func:
                        if datablock_type == 'IMAGE':
                            datablock = creation_func(uuid, creation_declaration['width'], creation_declaration['height'])
                        elif datablock_type == 'LIGHT':
                            datablock = creation_func(uuid, creation_declaration['light_type'])
                        else:
                            datablock = creation_func(uuid)
                        
                        uuid_manager.set_uuid(datablock, target_uuid=uuid)

                        if datablock_type == 'SCENE':
                            datablock.use_extra_user = True
                    else:
                        logger.log(f"[FN_ERROR] Unknown datablock type for creation: {datablock_type}")
                        continue
            else:
                logger.log(f"[FN_WARNING] No creation declaration found for UUID {uuid}. Skipping creation.")
                continue

        if datablock:
            logger.log(f"[FN_DEBUG] Applying overrides for datablock {datablock.name} ({uuid}).")
            _apply_overrides(datablock, tree, uuid)
            # After applying, we can remove the override entry as it's now "live"
            override_entry_idx = -1
            for i, item in enumerate(tree.fn_override_map):
                if item.datablock_uuid == uuid:
                    override_entry_idx = i
                    break
            
            if override_entry_idx != -1:
                logger.log(f"[FN_DEBUG] Removing override entry for {uuid} from fn_override_map after application.")
                tree.fn_override_map.remove(override_entry_idx)

    # --- 4. Synchronize States, Relationships, and Properties (Defensive Writes) ---
    logger.log("[FN_DEBUG] Phase 4: Synchronizing maps defensively.")

    # State Map Synchronization
    current_states = {item.node_id: item.datablock_uuids for item in tree.fn_state_map}
    for node_id, uuids in active_states.items():
        if current_states.get(node_id) != uuids:
            map_item = next((item for item in tree.fn_state_map if item.node_id == node_id), None)
            if not map_item:
                map_item = tree.fn_state_map.add()
                map_item.node_id = node_id
            map_item.datablock_uuids = uuids

    # Relationship Map Synchronization
    current_relationships = {(item.source_uuid, item.target_uuid, item.relationship_type) for item in tree.fn_relationships_map}
    active_rel_tuples = {(r['source_uuid'], r['target_uuid'], r['relationship_type']) for r in active_relationships}
    
    rels_to_add = active_rel_tuples - current_relationships
    
    for rel_tuple in rels_to_add:
        _link_relationship(rel_tuple)
        new_rel = tree.fn_relationships_map.add()
        new_rel.source_uuid, new_rel.target_uuid, new_rel.relationship_type = rel_tuple

    for assign in active_assignments:
        target_db = uuid_manager.find_datablock_by_uuid(assign['target_uuid'])
        if not target_db:
            continue

        prop_name = assign['property_name']
        
        plan_value = None
        if assign['value_type'] == 'UUID':
            plan_value = uuid_manager.find_datablock_by_uuid(assign['value_uuid'])
        elif assign['value_type'] == 'LITERAL':
            plan_value = json.loads(assign['value_json'])

        current_value = _get_nested_property(target_db, prop_name)

        if current_value != plan_value:
            if _set_nested_property(target_db, prop_name, plan_value):
                map_item = next((item for item in tree.fn_property_assignments_map if item.target_uuid == assign['target_uuid'] and item.property_name == prop_name), None)
                if not map_item:
                    map_item = tree.fn_property_assignments_map.add()
                    map_item.target_uuid = assign['target_uuid']
                    map_item.property_name = prop_name
                map_item.value_type = assign['value_type']
                map_item.value_uuid = assign['value_uuid']
                map_item.value_json = assign['value_json']


def _get_required_uuids_for_socket(socket, session_cache):
    """Traces the dependency graph backwards from a given socket to find all required UUIDs for that specific branch."""
    required_uuids = set()
    nodes_to_visit = {socket.node}
    visited_nodes = set()

    while nodes_to_visit:
        current_node = nodes_to_visit.pop()
        if current_node in visited_nodes:
            continue
        visited_nodes.add(current_node)

        node_results = session_cache.get(current_node.fn_node_id, {})
        for val in node_results.values():
            if isinstance(val, bpy.types.ID):
                required_uuids.add(uuid_manager.get_uuid(val))
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, bpy.types.ID):
                        required_uuids.add(uuid_manager.get_uuid(item))

        for input_socket in current_node.inputs:
            if input_socket.is_linked:
                nodes_to_visit.add(input_socket.links[0].from_node)
                
    return required_uuids

def _get_active_branch_node_ids(active_socket: bpy.types.NodeSocket) -> set:
    """Traces the dependency graph backwards from the active socket to find all node IDs in that branch."""
    branch_node_ids = set()
    nodes_to_visit = {active_socket.node}
    visited_nodes = set()

    while nodes_to_visit:
        current_node = nodes_to_visit.pop()
        if current_node in visited_nodes:
            continue
        visited_nodes.add(current_node)
        branch_node_ids.add(current_node.fn_node_id)

        for input_socket in current_node.inputs:
            if input_socket.is_linked:
                nodes_to_visit.add(input_socket.links[0].from_node)
    
    return branch_node_ids

def update_ui_for_active_socket(tree: bpy.types.NodeTree, active_socket: bpy.types.NodeSocket, session_cache: dict):
    """
    Handles UI updates for the active socket using a pre-filled cache.
    """
    for node in tree.nodes:
        for sock in node.outputs:
            sock.is_active = False
    _trace_active_path(active_socket, session_cache)

    # Get the UUID of the datablock that the active socket's node is responsible for
    # We get it from the session_cache, which holds the actual output of the node's execution
    node_results = session_cache.get(active_socket.node.fn_node_id)
    if not node_results:
        logger.log(f"[FN_DEBUG] update_ui_for_active_socket: No node results found for {active_socket.node.fn_node_id}")
        return

    final_output_uuid = node_results.get(active_socket.identifier)
    if not final_output_uuid:
        logger.log(f"[FN_DEBUG] update_ui_for_active_socket: No output UUID found for socket {active_socket.identifier} on node {active_socket.node.fn_node_id}")
        return

    logger.log(f"[FN_DEBUG] update_ui_for_active_socket: final_output_uuid = {final_output_uuid}")

    # Find the actual datablock in Blender using its UUID
    final_output_val = uuid_manager.find_datablock_by_uuid(final_output_uuid)
    logger.log(f"[FN_DEBUG] update_ui_for_active_socket: final_output_val = {final_output_val} (Type: {type(final_output_val).__name__ if final_output_val else 'None'})")

    if isinstance(final_output_val, bpy.types.Scene):
        logger.log(f"[FN_DEBUG] update_ui_for_active_socket: Setting bpy.context.window.scene to {final_output_val.name}")
        bpy.context.window.scene = final_output_val

def _evaluate_node(tree, node, session_cache, required_uuids, required_relationships, required_states, required_assignments, creation_declarations, load_file_declarations):
    """
    Recursively evaluates a node, populating the required state declarations.
    """
    if node.fn_node_id in session_cache:
        return session_cache[node.fn_node_id]

    kwargs = {'tree': tree}
    for input_socket in node.inputs:
        if input_socket.is_linked:
            link = input_socket.links[0]
            upstream_results = _evaluate_node(tree, link.from_node, session_cache, required_uuids, required_relationships, required_states, required_assignments, creation_declarations, load_file_declarations)
            value_from_upstream = upstream_results.get(link.from_socket.identifier) if isinstance(upstream_results, dict) else None

            is_ramified = len(link.from_socket.links) > 1
            is_mutable_input = input_socket.is_mutable

            if is_ramified and is_mutable_input and uuid_manager.is_valid_uuid(value_from_upstream):
                copy_id_key = f"{link.from_node.fn_node_id}:{link.from_socket.identifier}:{node.fn_node_id}:{input_socket.identifier}"
                map_item = next((item for item in tree.fn_state_map if item.node_id == copy_id_key), None)
                
                copied_uuid = None
                if map_item and map_item.datablock_uuids and ',' in map_item.datablock_uuids:
                    original_uuid_in_map, stored_copy_uuid = map_item.datablock_uuids.split(',', 1)
                    if original_uuid_in_map == value_from_upstream:
                        copied_uuid = stored_copy_uuid

                if copied_uuid:
                    value_to_pass = copied_uuid
                    required_states[copy_id_key] = map_item.datablock_uuids
                else:
                    new_uuid = uuid_manager.generate_uuid()
                    creation_declarations[new_uuid] = {
                        'type': 'COPY',
                        'source_uuid': value_from_upstream
                    }
                    required_states[copy_id_key] = f"{value_from_upstream},{new_uuid}"
                    required_uuids.add(new_uuid)
                    value_to_pass = new_uuid
                
                kwargs[input_socket.identifier] = value_to_pass
            else:
                # Ensure that any bpy.types.ID is converted to its UUID before passing to the node
                if isinstance(value_from_upstream, bpy.types.ID):
                    kwargs[input_socket.identifier] = uuid_manager.get_or_create_uuid(value_from_upstream)
                else:
                    kwargs[input_socket.identifier] = value_from_upstream
        else:
            kwargs[input_socket.identifier] = getattr(input_socket, 'default_value', None)
    
    node_results = node.execute(**kwargs) if hasattr(node, 'execute') else {}
    if node_results is None:
        node_results = {}

    if 'relationships' in node_results:
        for rel_tuple in node_results['relationships']:
            rel_dict = {
                'source_uuid': rel_tuple[0],
                'target_uuid': rel_tuple[1],
                'relationship_type': rel_tuple[2],
                'source_node_id': node.fn_node_id
            }
            required_relationships.append(rel_dict)
        del node_results['relationships']

    if 'states' in node_results:
        for state_key, state_value in node_results['states'].items():
            required_states[state_key] = state_value
        del node_results['states']

    if 'property_assignments' in node_results:
        for assignment in node_results['property_assignments']:
            assignment['source_node_id'] = node.fn_node_id # Tag assignment with its source
            required_assignments.append(assignment)
        del node_results['property_assignments']

    if 'declarations' in node_results:
        if 'derive_datablock' in node_results['declarations']:
            decl = node_results['declarations']['derive_datablock']
            creation_declarations[decl['derived_uuid']] = {
                'type': 'DERIVE',
                'source_uuid': decl['source_uuid'],
                'new_name': decl['new_name']
            }
            required_uuids.add(decl['derived_uuid'])
        elif 'load_file' in node_results['declarations']:
            decl = node_results['declarations']['load_file']
            load_file_declarations.append({
                'node_id': node.fn_node_id,
                'file_path': decl['file_path'],
                'link_flag': decl['link_flag'],
                'datablock_types': decl['datablock_types']
            })
        elif 'create_datablock' in node_results['declarations']:
            decl = node_results['declarations']['create_datablock']
            # For CREATE_DATABLOCK, the key in creation_declarations is the datablock's UUID
            creation_declarations[decl['uuid']] = decl
            required_uuids.add(decl['uuid'])
        # Add other declaration types here as they are implemented
        del node_results['declarations']

    session_cache[node.fn_node_id] = node_results

    for key, val in node_results.items():
        # If the node output is a UUID, add it to required_uuids
        if isinstance(val, str) and uuid_manager.is_valid_uuid(val):
            required_uuids.add(val)
        # If the node output is a dictionary containing a 'uuid' (like New Datablock's output)
        elif isinstance(val, dict) and 'uuid' in val and uuid_manager.is_valid_uuid(val['uuid']):
            required_uuids.add(val['uuid'])
            # Also store this declaration in creation_declarations if it's not already there
            # This is important for nodes like New Datablock where the output *is* the creation declaration
            if val['uuid'] not in creation_declarations:
                creation_declarations[val['uuid']] = val
        # Handle cases where nodes might still output bpy.types.ID directly (to be refactored)
        elif isinstance(val, bpy.types.ID):
            required_uuids.add(uuid_manager.get_or_create_uuid(val))
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and uuid_manager.is_valid_uuid(item):
                    required_uuids.add(item)
                elif isinstance(item, dict) and 'uuid' in item and uuid_manager.is_valid_uuid(item['uuid']):
                    required_uuids.add(item['uuid'])
                    if item['uuid'] not in creation_declarations:
                        creation_declarations[item['uuid']] = item
                elif isinstance(item, bpy.types.ID):
                    required_uuids.add(uuid_manager.get_or_create_uuid(item))

    return node_results

def _link_relationship(rel_tuple):
    source_uuid, target_uuid, rel_type = rel_tuple
    source_db = uuid_manager.find_datablock_by_uuid(source_uuid)
    target_db = uuid_manager.find_datablock_by_uuid(target_uuid)

    if not source_db or not target_db: return
    try:
        if rel_type == 'COLLECTION_OBJECT_LINK' and source_db.name not in target_db.objects:
            target_db.objects.link(source_db)
        elif rel_type == 'COLLECTION_CHILD_LINK' and source_db.name not in target_db.children:
            target_db.children.link(source_db)
        elif rel_type == 'OBJECT_SCENE_LINK' and isinstance(target_db, bpy.types.Scene) and source_db.name not in target_db.collection.objects:
            target_db.collection.objects.link(source_db)
        elif rel_type == 'COLLECTION_SCENE_LINK' and isinstance(target_db, bpy.types.Scene) and source_db.name not in target_db.collection.children:
            target_db.collection.children.link(source_db)
    except (RuntimeError, ReferenceError) as e:
        logger.log(f"  - Warning: Failed to link relationship {rel_tuple}: {e}")

def _unlink_relationship(rel_tuple):
    source_uuid, target_uuid, rel_type = rel_tuple
    source_db = uuid_manager.find_datablock_by_uuid(source_uuid)
    target_db = uuid_manager.find_datablock_by_uuid(target_uuid)

    if not source_db or not target_db: return
    try:
        if rel_type == 'COLLECTION_OBJECT_LINK' and source_db.name in target_db.objects:
            target_db.objects.unlink(source_db)
        elif rel_type == 'COLLECTION_CHILD_LINK' and source_db.name in target_db.children:
            target_db.children.unlink(source_db)
        elif rel_type == 'OBJECT_SCENE_LINK' and isinstance(target_db, bpy.types.Scene) and source_db.name in target_db.collection.objects:
            target_db.collection.objects.unlink(source_db)
        elif rel_type == 'COLLECTION_SCENE_LINK' and isinstance(target_db, bpy.types.Scene) and source_db.name in target_db.collection.children:
            target_db.collection.children.unlink(source_db)
    except (RuntimeError, ReferenceError) as e:
        logger.log(f"  - Warning: Failed to unlink relationship {rel_tuple}: {e}")

def _cleanup_state_map(tree, existing_node_ids):
    for i in range(len(tree.fn_state_map) - 1, -1, -1):
        if tree.fn_state_map[i].node_id.split(':')[0] not in existing_node_ids:
            tree.fn_state_map.remove(i)

def _trace_active_path(current_socket, session_cache):
    if not current_socket or current_socket.is_active:
        return
    current_socket.is_active = True
    for input_socket in current_socket.node.inputs:
        if input_socket.is_linked:
            _trace_active_path(input_socket.links[0].from_socket, session_cache)

def _get_managed_datablocks_in_scene() -> dict:
    managed_datablocks = {}
    collections = [bpy.data.objects, bpy.data.scenes, bpy.data.collections, bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights, bpy.data.cameras, bpy.data.worlds, bpy.data.node_groups, bpy.data.texts, bpy.data.actions, bpy.data.armatures]
    for collection in collections:
        for db in collection:
            if db.get(uuid_manager.FN_UUID_PROPERTY):
                managed_datablocks[db[uuid_manager.FN_UUID_PROPERTY]] = db
    return managed_datablocks

def _topological_sort_creation_declarations(creation_declarations):
    graph = {}
    in_degree = {}
    
    # Initialize graph and in-degrees
    for uuid, decl in creation_declarations.items():
        graph[uuid] = []
        in_degree[uuid] = 0

    # Build graph and calculate in-degrees
    for uuid, decl in creation_declarations.items():
        if decl['type'] == 'DERIVE' or decl['type'] == 'COPY':
            source_uuid = decl['source_uuid']
            if source_uuid in graph: # Ensure source is also a declared datablock in this batch
                graph[source_uuid].append(uuid)
                in_degree[uuid] += 1
            # else: source_uuid is not part of the current creation batch, assume it exists already

    # Kahn's algorithm for topological sort
    queue = [uuid for uuid, degree in in_degree.items() if degree == 0]
    sorted_uuids = []

    while queue:
        current_uuid = queue.pop(0)
        sorted_uuids.append(current_uuid)

        for neighbor_uuid in graph[current_uuid]:
            in_degree[neighbor_uuid] -= 1
            if in_degree[neighbor_uuid] == 0:
                queue.append(neighbor_uuid)

    if len(sorted_uuids) != len(creation_declarations):
        logger.log("[FN_WARNING] Cyclic dependency detected or some datablocks could not be sorted. Returning unsorted keys.")
        return list(creation_declarations.keys()) # Fallback to unsorted keys

    return sorted_uuids


def evaluate_node_for_output(tree, target_node):
    """
    Evaluates the necessary part of the tree to get the inputs for a specific node,
    without triggering a full depsgraph update.
    """
    session_cache = {}
    required_uuids = set()
    required_relationships = []
    required_states = {}
    required_assignments = []
    creation_declarations = {}
    load_file_declarations = []

    # We don't need the full recursive evaluation here, just the inputs for the target_node
    kwargs = {'tree': tree}
    datablocks_to_write = set()

    for input_socket in target_node.inputs:
        if input_socket.is_linked:
            link = input_socket.links[0]
            # Evaluate the upstream node that provides the input
            upstream_results = _evaluate_node(tree, link.from_node, session_cache, required_uuids, required_relationships, required_states, required_assignments, creation_declarations, load_file_declarations)
            value_from_upstream = upstream_results.get(link.from_socket.identifier)
            
            # Find the actual datablock from the UUID
            if uuid_manager.is_valid_uuid(value_from_upstream):
                db = uuid_manager.find_datablock_by_uuid(value_from_upstream)
                if db:
                    datablocks_to_write.add(db)
                kwargs[input_socket.identifier] = db
            elif isinstance(value_from_upstream, list):
                # Handle lists of UUIDs
                resolved_list = []
                for item in value_from_upstream:
                    if uuid_manager.is_valid_uuid(item):
                        db = uuid_manager.find_datablock_by_uuid(item)
                        if db:
                            datablocks_to_write.add(db)
                            resolved_list.append(db)
                kwargs[input_socket.identifier] = resolved_list
            else:
                kwargs[input_socket.identifier] = value_from_upstream
        else:
            kwargs[input_socket.identifier] = getattr(input_socket, 'default_value', None)

    return {"inputs": kwargs, "datablocks": datablocks_to_write}


def register():
    bpy.app.handlers.depsgraph_update_post.append(datablock_nodes_depsgraph_handler)

def unregister():
    # Find the handler and remove it
    for handler in bpy.app.handlers.depsgraph_update_post:
        if handler.__name__ == "datablock_nodes_depsgraph_handler":
            bpy.app.handlers.depsgraph_update_post.remove(handler)
            break