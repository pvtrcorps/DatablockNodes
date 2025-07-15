import bpy
import os
import sys
# Add the addon's parent directory to the Python path to ensure all modules are found
addon_dir = os.path.dirname(os.path.abspath(__file__))
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

# Now that the path is set, we can import the modules
import reconciler

def run_test():
    print("\n--- Running Refactoring Tests ---")

    # Clean up any existing node trees
    for tree in bpy.data.node_groups:
        if tree.bl_idname == 'DatablockTreeType':
            bpy.data.node_groups.remove(tree)

    # Create a new node tree
    tree = bpy.data.node_groups.new(name="TestDatablockTree", type='DatablockTreeType')
    print(f"Created node tree: {tree.name}")

    # --- Test 1: New Datablock Node ---
    print("\n--- Test 1: New Datablock Node ---")
    new_db_node = tree.nodes.new('FN_new_datablock')
    new_db_node.datablock_type = 'SCENE'
    new_db_node.inputs['Name'].default_value = "MyNewScene"
    new_db_node.location = (0, 0)

    # --- Test 2: Derive Datablock Node (CoW) ---
    print("\n--- Test 2: Derive Datablock Node (CoW) ---")
    derive_db_node = tree.nodes.new('FN_derive_datablock')
    derive_db_node.datablock_type = 'SCENE'
    derive_db_node.inputs['Name'].default_value = "DerivedScene"
    derive_db_node.location = (300, 0)
    tree.links.new(new_db_node.outputs['Scene'], derive_db_node.inputs['Source'])

    # --- Test 3: Link to Collection Node ---
    print("\n--- Test 3: Link to Collection Node ---")
    new_col_node = tree.nodes.new('FN_new_datablock')
    new_col_node.datablock_type = 'COLLECTION'
    new_col_node.inputs['Name'].default_value = "MyNewCollection"
    new_col_node.location = (0, -200)

    link_col_node = tree.nodes.new('FN_link_to_collection')
    link_col_node.location = (600, -200)
    tree.links.new(new_col_node.outputs['Collection'], link_col_node.inputs['Collection'])
    tree.links.new(new_db_node.outputs['Scene'], link_col_node.inputs['Collections']) # Link scene to collection

    # --- Test 4: Set Object Data Node ---
    print("\n--- Test 4: Set Object Data Node ---")
    new_obj_node = tree.nodes.new('FN_new_datablock')
    new_obj_node.datablock_type = 'OBJECT'
    new_obj_node.inputs['Name'].default_value = "MyNewObject"
    new_obj_node.location = (0, -400)

    new_mesh_node = tree.nodes.new('FN_new_datablock')
    new_mesh_node.datablock_type = 'MESH'
    new_mesh_node.inputs['Name'].default_value = "MyNewMesh"
    new_mesh_node.location = (0, -600)

    set_data_node = tree.nodes.new('FN_set_object_data')
    set_data_node.data_type = 'MESH'
    set_data_node.location = (300, -400)
    tree.links.new(new_obj_node.outputs['Object'], set_data_node.inputs['Object'])
    tree.links.new(new_mesh_node.outputs['Mesh'], set_data_node.inputs['Data'])

    # --- Test 5: Set Object Material Node ---
    print("\n--- Test 5: Set Object Material Node ---")
    new_mat_node = tree.nodes.new('FN_new_datablock')
    new_mat_node.datablock_type = 'MATERIAL'
    new_mat_node.inputs['Name'].default_value = "MyNewMaterial"
    new_mat_node.location = (0, -800)

    set_mat_node = tree.nodes.new('FN_set_object_material')
    set_mat_node.location = (300, -800)
    tree.links.new(new_obj_node.outputs['Object'], set_mat_node.inputs['Object'])
    tree.links.new(new_mat_node.outputs['Material'], set_mat_node.inputs['Material'])

    # --- Test 6: Set Object Parent Node ---
    print("\n--- Test 6: Set Object Parent Node ---")
    parent_obj_node = tree.nodes.new('FN_new_datablock')
    parent_obj_node.datablock_type = 'OBJECT'
    parent_obj_node.inputs['Name'].default_value = "ParentObj"
    parent_obj_node.location = (0, -1000)

    child_obj_node = tree.nodes.new('FN_new_datablock')
    child_obj_node.datablock_type = 'OBJECT'
    child_obj_node.inputs['Name'].default_value = "ChildObj"
    child_obj_node.location = (0, -1200)

    set_parent_node = tree.nodes.new('FN_set_object_parent')
    set_parent_node.location = (300, -1000)
    tree.links.new(parent_obj_node.outputs['Object'], set_parent_node.inputs['Parent'])
    tree.links.new(child_obj_node.outputs['Object'], set_parent_node.inputs['Childs'])

    # --- Test 7: Set Scene World Node ---
    print("\n--- Test 7: Set Scene World Node ---")
    new_world_node = tree.nodes.new('FN_new_datablock')
    new_world_node.datablock_type = 'WORLD'
    new_world_node.inputs['Name'].default_value = "MyNewWorld"
    new_world_node.location = (0, -1400)

    set_world_node = tree.nodes.new('FN_set_scene_world')
    set_world_node.location = (300, -1400)
    tree.links.new(new_db_node.outputs['Scene'], set_world_node.inputs['Scene'])
    tree.links.new(new_world_node.outputs['World'], set_world_node.inputs['World'])

    # --- Test 8: Import Datablock Node ---
    print("\n--- Test 8: Import Datablock Node ---")
    # Create a temporary object in the current scene to be imported/managed
    bpy.ops.mesh.primitive_cube_add(size=2, enter_editmode=False, align='WORLD', location=(0,0,0))
    bpy.context.object.name = "ImportedObject"
    imported_object = bpy.context.object

    import_db_node = tree.nodes.new('FN_import_datablock')
    import_db_node.datablock_type = 'OBJECT'
    import_db_node.datablock_name = imported_object.name # Use the name of the created object
    import_db_node.location = (0, -1600)

    

    # Set one of the final sockets as active to trigger execution
    new_db_node.outputs['Scene'].is_final_active = True

    # Manually trigger reconciliation for testing purposes
    reconciler.trigger_execution(tree)

    # Add a small delay to allow reconciliation to complete
    import time
    time.sleep(0.1)

    print("\n--- Verifying State After Execution ---")
    print(f"Number of state map items: {len(tree.fn_state_map)}")
    for item in tree.fn_state_map:
        print(f"  State Map Item: Node ID={item.node_id}, UUIDs={item.datablock_uuids}")

    print(f"Number of relationship map items: {len(tree.fn_relationships_map)}")
    for item in tree.fn_relationships_map:
        print(f"  Relationship Map Item: Source={item.source_uuid}, Target={item.target_uuid}, Type={item.relationship_type}")

    # Basic assertions (more detailed assertions would require inspecting Blender's state directly)
    assert len(tree.fn_state_map) > 0, "State map should not be empty"
    assert len(tree.fn_relationships_map) > 0, "Relationship map should not be empty"

    # Verify CoW for derived scene
    derived_scene_uuid = None
    original_scene_uuid = None
    for item in tree.fn_state_map:
        if new_db_node.fn_node_id in item.node_id and "Scene" in item.node_id:
            original_scene_uuid = item.datablock_uuids
        if derive_db_node.fn_node_id in item.node_id:
            parts = item.datablock_uuids.split(',')
            if len(parts) == 2:
                derived_scene_uuid = parts[1]
    
    assert original_scene_uuid is not None, "Original scene UUID not found in state map."
    assert derived_scene_uuid is not None, "Derived scene UUID not found in state map."
    assert original_scene_uuid != derived_scene_uuid, "CoW failed: Original and derived scene have the same UUID."

    print("\n--- Tests Completed Successfully ---")

    # Clean up dummy .blend file
    if os.path.exists(dummy_blend_path):
        os.remove(dummy_blend_path)
        print(f"Cleaned up dummy blend file: {dummy_blend_path}")
    
    

# Run the test
if __name__ == "__main__":
    run_test()