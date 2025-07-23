import bpy
from .. import logger, uuid_manager
from . import planner, materializer
from ..proxy_types import DatablockProxy
from ..properties import _datablock_creation_map

_is_executing = False

def _initialize_creation_map():
    """Populates the creation map if it's empty. Ensures bpy.data is ready."""
    if not _datablock_creation_map:
        logger.log("[Orchestrator] First execution: Initializing datablock creation map.")
        _datablock_creation_map.update({
            'SCENE': bpy.data.scenes.new,
            'COLLECTION': bpy.data.collections.new,
            'CAMERA': bpy.data.cameras.new,
            'IMAGE': bpy.data.images.new,
            'LIGHT': bpy.data.lights.new,
            'MATERIAL': bpy.data.materials.new,
            'MESH': bpy.data.meshes.new,
            'WORLD': bpy.data.worlds.new,
            'ARMATURE': bpy.data.armatures.new,
            'ACTION': bpy.data.actions.new,
        })

def execute_node_tree(tree, depsgraph):
    global _is_executing
    if _is_executing: return
    _is_executing = True
    try:
        _initialize_creation_map()
        final_root_proxy = _evaluate_active_branch(tree)
        if final_root_proxy:
            execution_plan = planner.plan_execution(final_root_proxy)
            _synchronize_blender_state(tree, execution_plan, depsgraph, final_root_proxy)
    finally:
        _is_executing = False

def _synchronize_blender_state(tree, plan: list, depsgraph, root_proxy):
    desired_uuids = {str(p.fn_uuid) for p in plan}
    current_datablocks = uuid_manager.get_all_managed_datablocks()
    current_uuids = set(current_datablocks.keys())

    uuids_to_destroy = current_uuids - desired_uuids
    
    if uuids_to_destroy:
        _destroy_datablocks_safely(uuids_to_destroy, current_datablocks)

    # The materializer now handles all creation, configuration, and linking.
    materializer.materialize_plan(plan, tree)
    
    bpy.context.view_layer.update()

    if root_proxy.properties.get('datablock_type') == 'SCENE':
        scene_db = uuid_manager.find_datablock_by_uuid(str(root_proxy.fn_uuid))
        if scene_db and bpy.context.window.scene != scene_db:
            bpy.context.window.scene = scene_db

def _destroy_datablocks_safely(uuids_to_destroy, all_managed_datablocks):
    """Destroys datablocks in a safe order to avoid ReferenceErrors."""
    logger.log(f"[Orchestrator] Starting safe destruction of {len(uuids_to_destroy)} datablocks.")
    
    partitions = {
        'OBJECT': [],
        'DATA': [],
        'COLLECTION': [],
        'SCENE': [],
        'OTHER': []
    }

    for uuid_str in uuids_to_destroy:
        db = all_managed_datablocks.get(uuid_str)
        if not db:
            continue
        
        try:
            db_type = db.bl_rna.identifier
            if db_type == 'OBJECT':
                partitions['OBJECT'].append(db)
            elif db_type == 'SCENE':
                partitions['SCENE'].append(db)
            elif db_type == 'COLLECTION':
                partitions['COLLECTION'].append(db)
            elif hasattr(db, 'users'):
                partitions['DATA'].append(db)
            else:
                partitions['OTHER'].append(db)
        except ReferenceError:
            logger.log(f"[Orchestrator] WARNING: Could not access a datablock during partitioning. It may have been already deleted.")

    # Destroy in a safe order: Content -> Containers
    for db in partitions['OBJECT']:
        try: bpy.data.objects.remove(db) 
        except ReferenceError: pass
    for db in partitions['DATA']:
        try:
            collection_name = db.bl_rna.identifier.lower() + 's'
            if hasattr(bpy.data, collection_name):
                getattr(bpy.data, collection_name).remove(db)
        except ReferenceError: pass
    for db in partitions['COLLECTION']:
        try: bpy.data.collections.remove(db)
        except ReferenceError: pass
    for db in partitions['SCENE']:
        try: bpy.data.scenes.remove(db)
        except ReferenceError: pass
    for db in partitions['OTHER']:
        try:
            collection_name = db.bl_rna.identifier.lower() + 's'
            if hasattr(bpy.data, collection_name):
                getattr(bpy.data, collection_name).remove(db)
        except ReferenceError: pass

    logger.log("[Orchestrator] Safe destruction complete.")

def _evaluate_active_branch(tree):
    active_socket = next((sock for node in tree.nodes for sock in node.outputs if sock.is_final_active), None)
    if not active_socket:
        return None
    session_cache = {}
    final_node_results = _evaluate_node(tree, active_socket.node, session_cache)
    final_value = final_node_results.get(active_socket.identifier)
    if isinstance(final_value, DatablockProxy):
        return final_value
    return None

def _evaluate_node(tree, node, session_cache):
    if node.fn_node_id in session_cache:
        return session_cache[node.fn_node_id]
    kwargs = {'tree': tree}
    for input_socket in node.inputs:
        if input_socket.is_linked:
            link = input_socket.links[0]
            upstream_results = _evaluate_node(tree, link.from_node, session_cache)
            kwargs[input_socket.identifier] = upstream_results.get(link.from_socket.identifier)
        else:
            if hasattr(input_socket, 'default_value'):
                kwargs[input_socket.identifier] = input_socket.default_value
            else:
                kwargs[input_socket.identifier] = None

    node_results = node.execute(**kwargs) if hasattr(node, 'execute') else {}
    session_cache[node.fn_node_id] = node_results
    return node_results