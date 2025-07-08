
import bpy
from . import uuid_manager

# --- Public API ---

def sync_active_socket(tree: bpy.types.NodeTree, active_socket: bpy.types.NodeSocket):
    """
    Synchronizes the Blender scene to match the state defined by the active node
    and its dependencies. This is the main entry point for the new engine.
    """
    print(f"--- [Reconciler] Syncing active socket: {active_socket.node.name}.{active_socket.identifier} ---")

    # 1. Evaluate the node tree "pull-style" starting from the active socket.
    # This phase creates/updates datablocks in memory and returns the desired final state.
    required_state, active_socket_evaluated_output = _evaluate_node_tree(tree, active_socket)
    
    # 2. Get the current managed state from the Blender scene.
    # This finds all datablocks that our addon currently manages.
    managed_datablocks_in_scene = _get_managed_datablocks_in_scene()

    # 3. Perform the diff and sync.
    # This primarily handles garbage collection (deleting what's no longer required).
    _diff_and_sync(required_state, managed_datablocks_in_scene)

    # 4. Set the active datablock in Blender based on the active socket's output
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

def _evaluate_node_tree(tree: bpy.types.NodeTree, active_socket: bpy.types.NodeSocket) -> tuple[dict, any]:
    """
    Performs a "pull" evaluation backwards from the active socket.
    It uses recursion with memoization (a cache) to avoid re-evaluating nodes.
    This function is the heart of the new engine.
    Returns a tuple: (all_managed_datablocks, active_socket_evaluated_output)
    """
    execution_cache = {}
    
    # The main recursive call, starting from the node of the active socket
    _evaluate_node(tree, active_socket.node, execution_cache)
    
    # The execution_cache now contains the results of all evaluated nodes.
    # We need to return a dictionary of all datablocks that are part of the final state.
    final_state = {}
    for node_id, result_dict in execution_cache.items():
        # result_dict is now a dictionary mapping socket_identifier to results
        if isinstance(result_dict, dict):
            for socket_id, result in result_dict.items():
                # We are interested in datablocks, which have UUIDs.
                if hasattr(result, 'get') and result.get(uuid_manager.FN_UUID_PROPERTY):
                    final_state[result[uuid_manager.FN_UUID_PROPERTY]] = result
                # Handle lists of datablocks
                elif isinstance(result, list):
                    for item in result:
                        if hasattr(item, 'get') and item.get(uuid_manager.FN_UUID_PROPERTY):
                            final_state[item[uuid_manager.FN_UUID_PROPERTY]] = item

    # Get the specific output of the active socket
    active_socket_evaluated_output = execution_cache.get(active_socket.node.fn_node_id, {}).get(active_socket.identifier)

    return final_state, active_socket_evaluated_output

def _evaluate_node(tree: bpy.types.NodeTree, node: bpy.types.Node, cache: dict):
    """
    Recursively evaluates a single node and its dependencies.
    """
    # Memoization: If node result is already in cache, return it.
    if node.fn_node_id in cache:
        return cache[node.fn_node_id]

    # Prepare kwargs for the node's execute method by evaluating its inputs first.
    kwargs = {'tree': tree}
    for input_socket in node.inputs:
        if input_socket.is_linked:
            # RECURSIVE CALL: Evaluate the node connected to this input.
            from_node = input_socket.links[0].from_node
            kwargs[input_socket.identifier] = _evaluate_node(tree, from_node, cache)
        else:
            # Use the socket's default value if it's not linked.
            if hasattr(input_socket, 'default_value'):
                kwargs[input_socket.identifier] = input_socket.default_value

    # Execute the node's logic with the prepared inputs.
    if hasattr(node, 'execute'):
        print(f"  - Evaluating: {node.name}")
        result_dict = node.execute(**kwargs)
        cache[node.fn_node_id] = result_dict
        return result_dict
    
    return {} # Return an empty dictionary if no execute method or no result


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

