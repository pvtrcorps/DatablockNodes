import bpy

from . import uuid_manager


# --- Main Reconciliation Flow ---

def execute_tree(tree: bpy.types.NodeTree):
    """Executes the node tree, handling datablock branching and dependencies centrally."""
    print("--- Starting Node Tree Execution ---")
    _print_node_tree_structure(tree)

    execution_cache = {}
    managed_datablocks_before_execution = _get_managed_datablocks(tree)
    print(f"Phase 1: Collected {len(managed_datablocks_before_execution)} previously managed datablocks.")

    print("Phase 2: Executing nodes in topological order...")
    try:
        sorted_nodes = _topological_sort(tree)
    except ValueError as e:
        print(f"Error: {e}")
        print("--- Node Tree Execution Aborted Due to Cycle ---")
        return

    for node in sorted_nodes:
        if not hasattr(node, 'execute'):
            print(f"  Node {node.name} (Type: {node.bl_idname}) has no execute method. Skipping.")
            continue

        print(f"  Executing node: {node.name} (Type: {node.bl_idname})")
        
        # 1. The reconciler prepares inputs, handling the branching logic.
        kwargs = _prepare_node_inputs(node, tree, execution_cache)
        
        # 2. The node's execute method is called. It now returns the output datablock.
        output_datablock = node.execute(**kwargs)
        
        # 3. The reconciler stores the output in the cache for subsequent nodes.
        if output_datablock:
            execution_cache[node.fn_node_id] = output_datablock

    _garbage_collect(tree, managed_datablocks_before_execution)
    print("--- Node Tree Execution Finished ---")
    _print_blender_data_overview()

def _prepare_node_inputs(node: bpy.types.Node, tree: bpy.types.NodeTree, execution_cache: dict) -> dict:
    """Prepares the input arguments for a node's execute method.
    This function contains the core branching logic, based on socket mutability.
    """
    kwargs = {}
    for input_socket in node.inputs:
        if not input_socket.is_linked:
            if hasattr(input_socket, 'default_value'):
                kwargs[input_socket.identifier] = input_socket.default_value
            elif input_socket.bl_idname.endswith('List'):
                kwargs[input_socket.identifier] = [] # Unlinked list socket should be an empty list
            else:
                kwargs[input_socket.identifier] = None # Unlinked single datablock socket should be None
            continue

        link = input_socket.links[0]
        from_socket = link.from_socket
        from_node = link.from_node
        
        datablock_from_cache = execution_cache.get(from_node.fn_node_id)
        if datablock_from_cache is None:
            continue

        # --- Intelligent Branching Logic ---
        # A copy is made ONLY if:
        # 1. The output socket has multiple links (it's a branch point).
        # 2. The input socket of the current node is marked as mutable (it intends to modify the datablock).
        is_branch_point = len(from_socket.links) > 1
        is_mutable_input = input_socket.is_mutable

        if is_branch_point and is_mutable_input:
            print(f"    - Branch detected from '{from_node.name}.{from_socket.name}' to mutable socket '{node.name}.{input_socket.name}'. Creating a copy.")
            
            # Check if this node already manages a copy from a previous execution.
            map_item = next((item for item in tree.fn_state_map if item.node_id == node.fn_node_id), None)
            existing_copy = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid) if map_item else None

            if existing_copy:
                # Reuse the existing copy if it's still valid.
                datablock_to_pass = existing_copy
                print(f"    - Reusing existing branch copy '{datablock_to_pass.name}'.")
            else:
                # Create a new copy and assign a new UUID.
                datablock_to_pass = datablock_from_cache.copy()
                print(f"    - After copy, before UUID set: '{datablock_to_pass.name}' (UUID: {uuid_manager.get_uuid(datablock_to_pass)})")
                uuid_manager.set_uuid(datablock_to_pass, force_new=True)
                print(f"    - Created new branch copy '{datablock_to_pass.name}' (UUID: {uuid_manager.get_uuid(datablock_to_pass)}).")
                
                # Register this new copy in the state map for persistence.
                if map_item:
                    map_item.datablock_uuid = uuid_manager.get_uuid(datablock_to_pass)
                else:
                    new_map_item = tree.fn_state_map.add()
                    new_map_item.node_id = node.fn_node_id
                    new_map_item.datablock_uuid = uuid_manager.get_uuid(datablock_to_pass)
            
            kwargs[input_socket.identifier] = datablock_to_pass
        else:
            # No copy needed: either not a branch point, or the socket is immutable.
            kwargs[input_socket.identifier] = datablock_from_cache
            
            # If this node was previously managing a copy (because it was a branch),
            # but now it's not, we must remove its entry from the state map.
            # This ensures proper garbage collection of the old copy.
            map_item_index = tree.fn_state_map.find(node.fn_node_id)
            if map_item_index != -1:
                print(f"    - Node '{node.name}' is no longer a branching node for '{input_socket.name}'. Removing from state map.")
                tree.fn_state_map.remove(map_item_index)

    kwargs['tree'] = tree
    return kwargs





def _topological_sort(tree: bpy.types.NodeTree) -> list:
    """Performs a topological sort on the node tree to determine execution order."""
    visited = set()      # Nodes whose processing is complete
    visiting = set()     # Nodes currently in the recursion stack (detects cycles)
    result = []          # The topologically sorted list of nodes

    def _dfs_visit(node):
        visiting.add(node)

        for output_socket in node.outputs:
            for link in output_socket.links:
                neighbor = link.to_node
                if neighbor in visiting:
                    raise ValueError(f"Cycle detected in node tree involving node: {neighbor.name}")
                if neighbor not in visited:
                    _dfs_visit(neighbor)
        
        visiting.remove(node)
        visited.add(node)
        result.insert(0, node) # Prepend to result to get correct order

    # Iterate over all nodes to ensure all components are visited
    for node in tree.nodes:
        if node not in visited:
            _dfs_visit(node)
            
    return result

# --- Utility Functions ---

def _get_managed_datablocks(tree: bpy.types.NodeTree) -> set:
    """Returns a set of UUIDs of datablocks currently managed by the tree."""
    return {item.datablock_uuid for item in tree.fn_state_map if hasattr(item, 'datablock_uuid')}



def _garbage_collect(tree: bpy.types.NodeTree, managed_datablocks_before_execution: set):
    """Removes datablocks that are no longer managed by the node tree.

    This works by comparing the set of managed UUIDs from before the execution
    with the set of managed UUIDs after the execution.
    """
    print("Phase 3: Garbage collecting...")
    
    managed_datablocks_after_execution = {item.datablock_uuid for item in tree.fn_state_map if hasattr(item, 'datablock_uuid') and item.node_id in {node.fn_node_id for node in tree.nodes}}
    stale_uuids = managed_datablocks_before_execution - managed_datablocks_after_execution
    
    if not stale_uuids:
        print("  - No stale datablocks to collect.")
    else:
        # Remove stale datablocks from Blender
        for uuid_to_remove in stale_uuids:
            datablock = uuid_manager.find_datablock_by_uuid(uuid_to_remove)
            if datablock:
                print(f"  - Deleting stale datablock '{datablock.name}' (UUID: {uuid_to_remove})")
                try:
                    
                    
                    if isinstance(datablock, bpy.types.Object):
                        bpy.data.objects.remove(datablock, do_unlink=True)
                    elif isinstance(datablock, bpy.types.Scene):
                        bpy.data.scenes.remove(datablock)
                    elif isinstance(datablock, bpy.types.Mesh):
                        bpy.data.meshes.remove(datablock)
                    elif isinstance(datablock, bpy.types.Material):
                        bpy.data.materials.remove(datablock)
                    # Add more datablock types as needed
                except ReferenceError:
                    print(f"  - Warning: Datablock '{datablock.name}' was already removed.")
            else:
                print(f"  - Warning: Stale datablock with UUID {uuid_to_remove} not found in Blender data.")

    # Clean up stale entries in fn_state_map
    nodes_in_tree = {node.fn_node_id for node in tree.nodes}
    items_to_remove = []
    for i, item in enumerate(tree.fn_state_map):
        if item.node_id not in nodes_in_tree:
            items_to_remove.append(i)
    
    # Remove in reverse order to avoid index issues
    for i in sorted(items_to_remove, reverse=True):
        tree.fn_state_map.remove(i)
    print(f"Garbage collection finished. Processed {len(stale_uuids)} stale items.")


def _print_node_tree_structure(tree: bpy.types.NodeTree):
    print("\n--- Node Tree Structure ---")
    for node in tree.nodes:
        print(f"Node: {node.name} (Type: {node.bl_idname})")
        print(f"  Location: ({node.location.x:.2f}, {node.location.y:.2f})")
        print("  Inputs:")
        for input_socket in node.inputs:
            linked_status = "Linked" if input_socket.is_linked else "Not Linked"
            socket_value = ""
            if not input_socket.is_linked and hasattr(input_socket, 'default_value'):
                socket_value = f", Value: {input_socket.default_value}"
            linked_from = ""
            if input_socket.is_linked:
                linked_nodes = [link.from_node.name for link in input_socket.links]
                linked_from = f" (from: {', '.join(linked_nodes)})";
            print(f"    - {input_socket.name} ({input_socket.bl_idname}): {linked_status}{linked_from}{socket_value}")
        print("  Outputs:")
        for output_socket in node.outputs:
            linked_status = "Linked" if output_socket.is_linked else "Not Linked"
            linked_to = "" # Output sockets link to input sockets
            if output_socket.is_linked:
                linked_nodes = [link.to_node.name for link in output_socket.links]
                linked_to = f" (to: {', '.join(linked_nodes)})";
            print(f"    - {output_socket.name} ({output_socket.bl_idname}): {linked_status}{linked_to}")
    print("---------------------------")

def _print_blender_data_overview():
    print("\n--- Blender Data Overview ---")

    print("\n--- Scenes ---")
    for scene in bpy.data.scenes:
        print(f"Scene: {scene.name}")
        _print_collection_contents(scene.collection, indent_level=1)

    print("\n--- Orphaned Collections (not in any scene hierarchy) ---")
    # Find all collections that are not part of any scene's hierarchy
    all_scene_collections = set()
    for scene in bpy.data.scenes:
        _collect_child_collections(scene.collection, all_scene_collections)

    orphaned_collections = [col for col in bpy.data.collections if col not in all_scene_collections]
    if orphaned_collections:
        for col in orphaned_collections:
            print(f"- Collection: {col.name}")
            _print_collection_contents(col, indent_level=1)
    else:
        print("  No orphaned collections.")

    print("\n--- Orphaned Objects (not in any collection) ---")
    # Find all objects that are not linked to any collection
    all_linked_objects = set()
    for col in bpy.data.collections:
        for obj in col.objects:
            all_linked_objects.add(obj)
    
    orphaned_objects = [obj for obj in bpy.data.objects if obj not in all_linked_objects]
    if orphaned_objects:
        for obj in orphaned_objects:
            parent_info = f" (Parent: {obj.parent.name})" if obj.parent else ""
            print(f"- Object: {obj.name}{parent_info}")
    else:
        print("  No orphaned objects.")

    print("-----------------------------")

def _print_collection_contents(collection, indent_level=0):
    indent = "  " * indent_level
    print(f"{indent}- Collection: {collection.name}")

    # Objects in this collection
    if collection.objects:
        print(f"{indent}  Objects:")
        for obj in collection.objects:
            parent_info = f" (Parent: {obj.parent.name})" if obj.parent else ""
            print(f"{indent}    - {obj.name}{parent_info}")

    # Child collections
    if collection.children:
        print(f"{indent}  Child Collections:")
        for child_col in collection.children:
            _print_collection_contents(child_col, indent_level + 2)

def _collect_child_collections(collection, collection_set):
    collection_set.add(collection)
    for child_col in collection.children:
        _collect_child_collections(child_col, collection_set)
