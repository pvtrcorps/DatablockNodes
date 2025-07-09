import bpy
import hashlib
import json
from bpy.app.handlers import persistent
from . import uuid_manager

# --- Continuous Execution Handler ---

# We need a single, identifiable timer function for the debounce to work correctly.
_timer_func = None

# A tuple of node idnames that should not be cached
ACTION_NODES = (
    'FN_link_to_scene',
    'FN_write_file',
    'FN_new_datablock',
    # 'FN_link_to_collection', # Temporarily commented out for testing
)


@persistent
def datablock_nodes_depsgraph_handler(scene, depsgraph):
    """
    This function is registered with bpy.app.handlers.depsgraph_update_post.
    It gets called anytime the dependency graph is updated.
    """
    global _timer_func

    # It's more robust to iterate through all node groups than rely on context
    active_tree = None
    for tree in bpy.data.node_groups:
        if hasattr(tree, 'bl_idname') and tree.bl_idname == 'DatablockTreeType':
            # Check if this tree has a final active socket.
            if any(sock.is_final_active for node in tree.nodes for sock in node.outputs):
                active_tree = tree
                break
    
    if not active_tree:
        return

    # --- Debounce mechanism --- #
    def execution_wrapper():
        """A wrapper to pass the tree to the actual execution trigger."""
        global _timer_func
        print(f"[FN_Handler] Timer expired for '{active_tree.name}', triggering execution.")
        trigger_execution(active_tree)
        _timer_func = None # Clear the global timer function reference
        return None # Returning None stops the timer from repeating

    # If a timer is already registered, cancel it before setting a new one.
    if _timer_func and bpy.app.timers.is_registered(_timer_func):
        bpy.app.timers.unregister(_timer_func)
    
    # Store the new wrapper and register it.
    _timer_func = execution_wrapper
    bpy.app.timers.register(_timer_func, first_interval=0.05)



def trigger_execution(tree: bpy.types.NodeTree):
    """
    Finds the final active output socket in the tree and starts the sync process.
    This is called by the timer to start the evaluation.
    """
    print("--- [Reconciler] Continuous execution triggered ---")
    final_socket = None
    for node in tree.nodes:
        for socket in node.outputs:
            if socket.is_final_active:
                final_socket = socket
                break
        if final_socket:
            break
    
    if final_socket:
        sync_active_socket(tree, final_socket)
    else:
        print("--- [Reconciler] No final active socket found. Skipping execution. ---")


# --- Public API ---

def sync_active_socket(tree: bpy.types.NodeTree, active_socket: bpy.types.NodeSocket):
    """
    Synchronizes the Blender scene to match the state defined by the active node
    and its dependencies. This is the main entry point for the new engine.
    """
    print(f"--- [Reconciler] Syncing active socket: {active_socket.node.name}.{active_socket.identifier} ---")
    # TEMPORARY: Clear the entire execution cache for debugging
    if 'fn_execution_cache' in tree:
        del tree['fn_execution_cache']
        print("--- [Reconciler] TEMPORARY: Cleared fn_execution_cache ---")

    # 1. Evaluate the node tree "pull-style" starting from the active socket.
    # This phase creates/updates datablocks in memory and returns the desired final state.
    required_state, active_socket_evaluated_output, evaluated_nodes_and_sockets = _evaluate_node_tree(tree, active_socket)
    
    # 2. Get the current managed state from the Blender scene.
    # This finds all datablocks that our addon currently manages.
    managed_datablocks_in_scene = _get_managed_datablocks_in_scene()

    print(f"  - GC Debug: Required UUIDs: {list(required_state.keys())}")
    print(f"  - GC Debug: Current Managed UUIDs: {list(managed_datablocks_in_scene.keys())}")

    # 3. Perform the diff and sync.
    # This primarily handles garbage collection (deleting what's no longer required).
    _diff_and_sync(required_state, managed_datablocks_in_scene)

    # 4. Reset all is_active flags
    for node in tree.nodes:
        for sock in node.outputs:
            sock.is_active = False

    # 5. Trace the active path and set is_active flags
    _trace_active_path(active_socket, evaluated_nodes_and_sockets)

    # 6. Set the active datablock in Blender based on the active socket's output
    if active_socket_evaluated_output is not None:
        target_datablock = None
        # If the output is a dictionary (from a node returning {socket_id: value})
        if isinstance(active_socket_evaluated_output, dict):
            # Get the actual value from the dictionary using the active socket's identifier
            active_socket_evaluated_output = active_socket_evaluated_output.get(active_socket.identifier)

        if isinstance(active_socket_evaluated_output, list):
            if active_socket_evaluated_output:
                target_datablock = active_socket_evaluated_output[0] # Take the first item from the list
        else:
            target_datablock = active_socket_evaluated_output

        if target_datablock:
            # If the target_datablock is still a dictionary (e.g., from a node's output dict)
            if isinstance(target_datablock, dict):
                # Assuming it's a single output, get its value
                target_datablock = next(iter(target_datablock.values()), None)

            if isinstance(target_datablock, bpy.types.Scene):
                bpy.context.view_layer.update() # Force dependency graph update
                bpy.context.window.scene = target_datablock
                print(f"  - Set active scene to: {target_datablock.name}")
            elif isinstance(target_datablock, bpy.types.Object):
                # Set active object and select it
                bpy.context.view_layer.objects.active = target_datablock
                target_datablock.select_set(True)
                print(f"  - Set active object to: {target_datablock.name}")
            # Add more types as needed (e.g., Collection, World, etc.)
            else:
                print(f"  - No specific activation logic for type: {type(target_datablock).__name__}")

    print(f"--- [Reconciler] Sync finished ---")

# --- Core Logic ---

def _evaluate_node_tree(tree: bpy.types.NodeTree, active_socket: bpy.types.NodeSocket) -> tuple[dict, any, dict]:
    """
    Performs a "pull" evaluation backwards from the active socket.
    It uses recursion with memoization (a cache) to avoid re-evaluating nodes.
    This function is the heart of the new engine.
    Returns a tuple: (all_managed_datablocks, active_socket_evaluated_output, evaluated_nodes_and_sockets)
    """
    # This is a session cache, it's cleared for every full execution run.
    # It stores (result_dict, hash) tuples.
    session_cache = {}
    evaluated_nodes_and_sockets = {}
    
    # The main recursive call, starting from the node of the active socket
    _evaluate_node(tree, active_socket.node, session_cache, evaluated_nodes_and_sockets)
    
    # The session_cache now contains the results of all evaluated nodes.
    # We need to return a dictionary of all datablocks that are part of the final state.
    final_state = {}
    active_socket_evaluated_output = None # Initialize to None

    # Iterate through the session_cache to build final_state and get active_socket_evaluated_output
    for node_id, (result_dict, result_hash) in session_cache.items():
        # Build final_state
        if isinstance(result_dict, dict):
            for socket_id, result in result_dict.items():
                if isinstance(result, str) and result.startswith('uuid:'):
                    uuid = result.split(':')[1]
                    # Add UUID to final_state directly, regardless of whether datablock is found immediately
                    final_state[uuid] = None # Store None as a placeholder for now
                    # We still try to find it to get the actual datablock if available
                    datablock = uuid_manager.find_datablock_by_uuid(uuid)
                    if datablock:
                        final_state[uuid] = datablock # Update with actual datablock if found
                elif isinstance(result, list):
                    for item in result:
                        if isinstance(item, str) and item.startswith('uuid:'):
                            uuid = item.split(':')[1]
                            final_state[uuid] = None # Store None as a placeholder
                            datablock = uuid_manager.find_datablock_by_uuid(uuid)
                            if datablock:
                                final_state[uuid] = datablock # Update with actual datablock if found
        
        # Get active_socket_evaluated_output if this is the active node
        if node_id == active_socket.node.fn_node_id:
            if isinstance(result_dict, dict):
                active_socket_evaluated_output = result_dict.get(active_socket.identifier)
                # If it's a UUID string, resolve it to the actual datablock
                if isinstance(active_socket_evaluated_output, str) and active_socket_evaluated_output.startswith('uuid:'):
                    active_socket_evaluated_output = uuid_manager.find_datablock_by_uuid(active_socket_evaluated_output.split(':')[1])
            elif isinstance(result_dict, list): # Handle list outputs for active socket
                # If the active socket is a list, we might need to resolve all items
                resolved_list = []
                for item in result_dict:
                    if isinstance(item, str) and item.startswith('uuid:'):
                        resolved_list.append(uuid_manager.find_datablock_by_uuid(item.split(':')[1]))
                    else:
                        resolved_list.append(item)
                active_socket_evaluated_output = resolved_list

    return final_state, active_socket_evaluated_output, evaluated_nodes_and_sockets

def _evaluate_node(tree: bpy.types.NodeTree, node: bpy.types.Node, cache: dict, evaluated_nodes_and_sockets: dict):
    """
    Recursively evaluates a single node and its dependencies, using a cache to avoid re-evaluation.
    Returns a tuple: (result_dictionary, result_hash)
    """
    # If this node's result is already in the session cache, return it immediately.
    if node.fn_node_id in cache:
        return cache[node.fn_node_id]

    hasher = hashlib.sha256()
    node.update_hash(hasher)  # Start hash with the node's own static properties

    kwargs = {'tree': tree}
    input_hashes = []

    # --- Special Handling for Switch Node ---
    if node.bl_idname == "FN_switch":
        print(f"  - Evaluating Switch Node: {node.name}")
        control_socket_name = 'Switch' if node.switch_type == 'BOOLEAN' else 'Index'
        control_socket = node.inputs.get(control_socket_name)
        control_value = None
        control_hash = ''

        # 1. Evaluate the control socket first
        if control_socket.is_linked:
            link = control_socket.links[0]
            upstream_dict, upstream_hash = _evaluate_node(tree, link.from_node, cache, evaluated_nodes_and_sockets)
            control_hash = upstream_hash
            if upstream_dict:
                control_value = upstream_dict.get(link.from_socket.identifier)
        else:
            control_value = control_socket.default_value
            control_hash = str(control_value) # Simple hash for default value

        hasher.update(control_hash.encode())
        kwargs[control_socket.identifier] = control_value
        
        # 2. Determine the active data socket based on the control value
        active_socket_name = None
        if node.switch_type == 'BOOLEAN':
            active_socket_name = 'True' if control_value else 'False'
        elif node.switch_type == 'INDEX' and isinstance(control_value, int):
            if 0 <= control_value < node.item_count:
                active_socket_name = str(control_value)

        # 3. Evaluate only the active branch
        output_value = None
        if active_socket_name:
            active_socket = node.inputs.get(active_socket_name)
            if active_socket and active_socket.is_linked:
                link = active_socket.links[0]
                # RECURSIVE CALL for the active branch
                upstream_dict, upstream_hash = _evaluate_node(tree, link.from_node, cache, evaluated_nodes_and_sockets)
                input_hashes.append(upstream_hash) # Add active branch hash to the main hash
                if upstream_dict:
                    output_value = upstream_dict.get(link.from_socket.identifier)
            elif active_socket: # Unlinked but exists
                output_value = getattr(active_socket, 'default_value', None)
                # Add default value to hash
                input_hashes.append(str(tuple(output_value) if isinstance(output_value, (list, bpy.types.bpy_prop_array)) else output_value))

        # All other kwargs for the switch execute are None
        for input_socket in node.inputs:
            if input_socket.identifier not in kwargs:
                 kwargs[input_socket.identifier] = None
        
        # The final output of the switch node is just the value from the active branch
        kwargs[node.outputs[0].identifier] = output_value
        
        # Finalize the hash and check cache
        for h in sorted(input_hashes):
            hasher.update(h.encode())
        current_hash = hasher.hexdigest()

        # --- Cache Check for Switch ---
        # (This part is now combined with the main cache check below)

    # --- Normal Evaluation for other nodes ---
    else:
        for input_socket in node.inputs:
            if input_socket.is_linked:
                link = input_socket.links[0]
                from_node = link.from_node
                from_socket = link.from_socket

                upstream_result_dict, upstream_hash = _evaluate_node(tree, from_node, cache, evaluated_nodes_and_sockets)
                input_hashes.append(upstream_hash)
                
                if upstream_result_dict and isinstance(upstream_result_dict, dict):
                    kwargs[input_socket.identifier] = upstream_result_dict.get(from_socket.identifier)
                else:
                    kwargs[input_socket.identifier] = None
            else:
                val = getattr(input_socket, 'default_value', None)
                kwargs[input_socket.identifier] = val
                if val is not None:
                    hasher.update(str(tuple(val) if isinstance(val, (list, bpy.types.bpy_prop_array)) else val).encode())

    # --- Hashing, Caching, and Execution (Common for all nodes) ---
    if node.bl_idname != "FN_switch": # Hash for normal nodes was not finalized yet
        for h in sorted(input_hashes):
            hasher.update(h.encode())
        current_hash = hasher.hexdigest()

    skip_cache = node.bl_idname in ACTION_NODES

    cached_entry = None
    if not skip_cache:
        for entry in tree.fn_execution_cache:
            if entry.node_id == node.fn_node_id and entry.hash == current_hash:
                cached_entry = entry
                break

    if cached_entry:
        print(f"  - Cache HIT for: {node.name}")
        cached_data = json.loads(cached_entry.result_json)
        cache[node.fn_node_id] = (cached_data, current_hash)
        # We still need to populate evaluated_nodes_and_sockets for path tracing
        # This reconstruction is a simplification and might need to be more robust
        evaluated_nodes_and_sockets[node.fn_node_id] = {
            "node": node,
            "output_sockets": {s.identifier: s for s in node.outputs},
            "input_sockets_values": kwargs # Use the kwargs we've already built
        }
        return cached_data, current_hash

    if skip_cache:
        print(f"  - Executing non-cacheable node type: {node.name}")
    else:
        print(f"  - Cache MISS for: {node.name} (Hash: {current_hash[:7]}...)")

    if hasattr(node, 'execute'):
        resolved_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str) and value.startswith('uuid:'):
                resolved_kwargs[key] = uuid_manager.find_datablock_by_uuid(value.split(':')[1])
            else:
                resolved_kwargs[key] = value
        
        result_dict = node.execute(**resolved_kwargs)
        
        uuid_result_dict = {}
        if result_dict:
            for key, value in result_dict.items():
                if isinstance(value, bpy.types.ID):
                    uuid_result_dict[key] = f"uuid:{uuid_manager.get_or_create_uuid(value)}"
                elif isinstance(value, list) and all(isinstance(i, bpy.types.ID) for i in value):
                    uuid_result_dict[key] = [f"uuid:{uuid_manager.get_or_create_uuid(i)}" for i in value]
                else:
                    uuid_result_dict[key] = value

        if not skip_cache:
            cache_entry = next((e for e in tree.fn_execution_cache if e.node_id == node.fn_node_id), None)
            if not cache_entry:
                cache_entry = tree.fn_execution_cache.add()
                cache_entry.node_id = node.fn_node_id
            cache_entry.hash = current_hash
            cache_entry.result_json = json.dumps(uuid_result_dict)

        cache[node.fn_node_id] = (uuid_result_dict, current_hash)
        evaluated_nodes_and_sockets[node.fn_node_id] = {
            "node": node,
            "output_sockets": {s.identifier: s for s in node.outputs},
            "input_sockets_values": kwargs
        }
        return uuid_result_dict, current_hash
    
    return {}, current_hash

def _trace_active_path(current_socket: bpy.types.NodeSocket, evaluated_nodes_and_sockets: dict):
    """
    Recursively traces the active path backwards from the current_socket
    and sets the is_active flag for all sockets in the path.
    """
    if not current_socket:
        return

    # Mark the current socket as active
    current_socket.is_active = True

    # Get the node that owns this socket
    current_node = current_socket.node

    # Get the evaluated info for this node
    node_info = evaluated_nodes_and_sockets.get(current_node.fn_node_id)
    if not node_info:
        return

    # Find which input socket(s) contributed to the current_socket's output
    # This logic depends on how each node's execute method works.
    # For now, we'll assume that if an input socket is linked and its value
    # was used to produce the output, it's part of the active path.
    # This is a simplification and might need refinement for complex nodes (e.g., Switch).

    # For a Switch node, only the selected input should be active.
    if current_node.bl_idname == "FN_switch":
        switch_type = current_node.switch_type
        if switch_type == 'BOOLEAN':
            switch_value = node_info["input_sockets_values"].get(current_node.inputs['Switch'].identifier)
            if switch_value is True:
                # Trace back through the 'True' input
                true_input_socket = current_node.inputs.get('True')
                if true_input_socket and true_input_socket.is_linked:
                    _trace_active_path(true_input_socket.links[0].from_socket, evaluated_nodes_and_sockets)
            else:
                # Trace back through the 'False' input
                false_input_socket = current_node.inputs.get('False')
                if false_input_socket and false_input_socket.is_linked:
                    _trace_active_path(false_input_socket.links[0].from_socket, evaluated_nodes_and_sockets)
        elif switch_type == 'INDEX':
            index = node_info["input_sockets_values"].get(current_node.inputs['Index'].identifier)
            if index is not None:
                item_input_socket = current_node.inputs.get(str(index))
                if item_input_socket and item_input_socket.is_linked:
                    _trace_active_path(item_input_socket.links[0].from_socket, evaluated_nodes_and_sockets)
    else:
        # For other nodes, assume all linked inputs contributed (simplification)
        for input_socket in current_node.inputs:
            if input_socket.is_linked:
                _trace_active_path(input_socket.links[0].from_socket, evaluated_nodes_and_sockets)


def _get_managed_datablocks_in_scene() -> dict:
    """
    Finds all datablocks in the current Blender file that have a `_fn_uuid`
    and returns them as a dictionary of {uuid: datablock}.
    """
    managed_datablocks = {}
    
    # List of all bpy.data collections to scan
    datablock_collections = [
        bpy.data.objects, bpy.data.scenes, bpy.data.collections,
        bpy.data.meshes, bpy.data.materials, bpy.data.images,
        bpy.data.lights, bpy.data.cameras, bpy.data.worlds,
        bpy.data.node_groups, bpy.data.texts, bpy.data.actions
    ]

    for collection in datablock_collections:
        for datablock in collection:
            # Use .get() for safety, returns None if property doesn't exist.
            uuid = datablock.get(uuid_manager.FN_UUID_PROPERTY)
            if uuid:
                managed_datablocks[uuid] = datablock
                
    return managed_datablocks


def _diff_and_sync(required_state: dict, current_state: dict):
    """
    Compares the required state with the current state and applies changes.
    In our new model, creation and updates happen during evaluation.
    This function's main role is GARBAGE COLLECTION.
    """
    required_uuids = set(required_state.keys())
    current_uuids = set(current_state.keys())

    # --- Garbage Collection ---
    uuids_to_delete = current_uuids - required_uuids
    
    if not uuids_to_delete:
        print("  - Garbage Collection: No stale datablocks to remove.")
        return

    print(f"  - Garbage Collection: Found {len(uuids_to_delete)} stale datablocks to remove.")

    # Map datablock types to their corresponding bpy.data collection for removal
    removal_map = {
        bpy.types.Object: bpy.data.objects,
        bpy.types.Scene: bpy.data.scenes,
        bpy.types.Mesh: bpy.data.meshes,
        bpy.types.Material: bpy.data.materials,
        bpy.types.Image: bpy.data.images,
        bpy.types.Camera: bpy.data.cameras,
        bpy.types.Light: bpy.data.lights,
        bpy.types.NodeTree: bpy.data.node_groups,
        bpy.types.Text: bpy.data.texts,
        bpy.types.Collection: bpy.data.collections,
        bpy.types.World: bpy.data.worlds,
    }

    for uuid in uuids_to_delete:
        datablock = current_state[uuid]
        remover_collection = removal_map.get(type(datablock))
        
        if remover_collection:
            try:
                print(f"    - Deleting stale datablock '{datablock.name}' (UUID: {uuid})")
                remover_collection.remove(datablock)
            except (ReferenceError, RuntimeError):
                # This can happen if the datablock was already removed as a dependency
                print(f"    - Warning: Datablock with UUID {uuid} was already removed.")
        else:
            print(f"    - Warning: No removal handler for type '{type(datablock).__name__}'")

def _set_rna_property_value(rna_object: bpy.types.bpy_struct, rna_path: str, value):
    """
    Sets the value of an RNA property, handling nested paths.
    rna_object: The bpy.types.bpy_struct instance (e.g., bpy.data.objects['Cube'])
    rna_path: The path to the property (e.g., 'location', 'location[0]', 'cycles.diffuse_color')
    value: The value to set.
    """
    parts = rna_path.split('.')
    current_obj = rna_object
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            # Last part, set the value
            try:
                # Handle array access (e.g., 'location[0]')
                if '[' in part and part.endswith(']'):
                    prop_name = part.split('[')[0]
                    index = int(part.split('[')[1][:-1])
                    if hasattr(current_obj, prop_name):
                        current_obj[prop_name][index] = value
                else:
                    setattr(current_obj, part, value)
            except AttributeError:
                print(f"[Reconciler] Warning: Property '{rna_path}' not found on {rna_object.name}.")
            except TypeError:
                print(f"[Reconciler] Warning: Type mismatch for property '{rna_path}' on {rna_object.name}. Value: {value}")
            except Exception as e:
                print(f"[Reconciler] Error setting property '{rna_path}' on {rna_object.name}: {e}")
        else:
            # Navigate to the next nested object
            try:
                current_obj = getattr(current_obj, part)
            except AttributeError:
                print(f"[Reconciler] Warning: Nested property path '{part}' not found on {current_obj.name}.")
                return # Cannot proceed if path is broken

def _get_evaluated_inputs(tree: bpy.types.NodeTree, node: bpy.types.Node, cache: dict) -> dict:
    """
    Evaluates all inputs of a given node and returns a dictionary of their evaluated values.
    """
    evaluated_inputs = {}
    for input_socket in node.inputs:
        if input_socket.is_linked:
            from_node = input_socket.links[0].from_node
            evaluated_inputs[input_socket.identifier] = _evaluate_node(tree, from_node, cache)
        else:
            if hasattr(input_socket, 'default_value'):
                evaluated_inputs[input_socket.identifier] = input_socket.default_value
            else:
                evaluated_inputs[input_socket.identifier] = None # Default for unlinked sockets without default_value
    return evaluated_inputs

def evaluate_node_for_output(tree: bpy.types.NodeTree, output_node: bpy.types.Node) -> dict:
    """
    Evaluates the necessary part of the tree to get the inputs for a specific
    output/action node (like Write File) and returns a dictionary of all evaluated inputs.
    """
    print(f"--- [Reconciler] Evaluating inputs for action node: {output_node.name} ---")
    execution_cache = {}
    
    # Evaluate all inputs of the target node
    evaluated_inputs = _get_evaluated_inputs(tree, output_node, execution_cache)

    # Collect all datablocks from the evaluated inputs
    datablocks_for_output = set()
    for key, value in evaluated_inputs.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, bpy.types.ID):
                    datablocks_for_output.add(item)
        elif isinstance(value, bpy.types.ID):
            datablocks_for_output.add(value)

    # Return both the evaluated inputs (for properties like file_path) and the collected datablocks
    return {
        "inputs": evaluated_inputs,
        "datablocks": datablocks_for_output
    }