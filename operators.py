
import bpy
import os
from . import reconciler

class FN_OT_activate_socket(bpy.types.Operator):
    """Activates a socket and triggers the scene synchronization."""
    bl_idname = "fn.activate_socket"
    bl_label = "Activate Socket"

    node_id: bpy.props.StringProperty()
    socket_identifier: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        target_node = next((n for n in node_tree.nodes if n.fn_node_id == self.node_id), None)

        if not target_node:
            self.report({'ERROR'}, f"Node with ID {self.node_id} not found.")
            return {'CANCELLED'}

        target_socket = next((s for s in target_node.outputs if s.identifier == self.socket_identifier), None)

        if not target_socket:
            self.report({'ERROR'}, f"Socket with identifier {self.socket_identifier} not found on node {self.node_id}.")
            return {'CANCELLED'}

        # Deactivate all other active sockets in the tree
        for node in node_tree.nodes:
            for sock in node.outputs:
                sock.is_active = False
                sock.is_final_active = False

        # Set the active property on the target socket
        target_socket.is_active = True
        target_socket.is_final_active = True

        # Call the reconciler
        reconciler.sync_active_socket(node_tree, target_socket)

        return {'FINISHED'}

class FN_OT_write_file(bpy.types.Operator):
    """Executes the write file operation from a node."""
    bl_idname = "fn.write_file"
    bl_label = "Write File Node"

    node_id: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        write_node = next((n for n in node_tree.nodes if n.fn_node_id == self.node_id), None)

        if not write_node:
            self.report({'ERROR'}, f"Node with ID {self.node_id} not found.")
            return {'CANCELLED'}

        # --- 1. Evaluate the node tree to get the inputs ---
        # We use a dedicated evaluation function for this action.
        evaluated_output = reconciler.evaluate_node_for_output(node_tree, write_node)
        file_path = evaluated_output["inputs"].get(write_node.inputs["File Path"].identifier)
        overwrite = evaluated_output["inputs"].get(write_node.inputs["Overwrite"].identifier)
        datablocks_to_write = evaluated_output["datablocks"]

        if not datablocks_to_write:
            self.report({'WARNING'}, "No datablocks to write.")
            return {'CANCELLED'}

        # --- 2. Check for overwrite ---
        if os.path.exists(file_path) and not overwrite:
            self.report({'ERROR'}, f"File exists and overwrite is off: {file_path}")
            return {'CANCELLED'}

        # --- 3. Write to file ---
        try:
            bpy.data.libraries.write(file_path, datablocks_to_write)
            self.report({'INFO'}, f"Successfully wrote {len(datablocks_to_write)} datablocks to {file_path}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to write file: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

class FN_OT_add_property_to_set(bpy.types.Operator):
    """Adds a property to the Set Datablock Properties node."""
    bl_idname = "fn.add_property_to_set"
    bl_label = "Add Property"

    node_id: bpy.props.StringProperty()
    datablock_type: bpy.props.StringProperty()
    is_cycles_property: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        node = next((n for n in node_tree.nodes if n.fn_node_id == self.node_id), None)

        if not node:
            self.report({'ERROR'}, "Node not found.")
            return {'CANCELLED'}

        prop_item = node.properties_to_set.add()
        prop_item.name = "New Property"
        # Default socket type, will be updated when rna_path is set
        prop_item.socket_type = "STRING"

        # Force update sockets to reflect the new property
        node.update_sockets(context)
        return {'FINISHED'}

class FN_OT_remove_property_from_set(bpy.types.Operator):
    """Removes a property from the Set Datablock Properties node."""
    bl_idname = "fn.remove_property_from_set"
    bl_label = "Remove Property"

    node_id: bpy.props.StringProperty()
    property_index: bpy.props.IntProperty()

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        node = next((n for n in node_tree.nodes if n.fn_node_id == self.node_id), None)

        if not node:
            self.report({'ERROR'}, "Node not found.")
            return {'CANCELLED'}

        node.properties_to_set.remove(self.property_index)

        # Force update sockets to reflect the removed property
        node.update_sockets(context)
        return {'FINISHED'}


_all_operators = (
    FN_OT_activate_socket,
    FN_OT_write_file,
    FN_OT_add_property_to_set,
    FN_OT_remove_property_from_set,
)

def register():
    print("Registering operators...")
    for cls in _all_operators:
        bpy.utils.register_class(cls)
        print(f"  Registered: {cls.bl_idname}")

def unregister():
    print("Unregistering operators...")
    for cls in reversed(_all_operators):
        bpy.utils.unregister_class(cls)
        print(f"  Unregistered: {cls.bl_idname}")
