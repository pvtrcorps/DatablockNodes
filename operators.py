
import bpy
import os
from . import reconciler

class FN_OT_activate_socket(bpy.types.Operator):
    """Activates a socket, sets it as the final execution point, and triggers sync."""
    bl_idname = "fn.activate_socket"
    bl_label = "Activate and Sync Socket"

    node_id: bpy.props.StringProperty()
    socket_identifier: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        
        # Find the target node and socket
        target_node = next((n for n in node_tree.nodes if n.fn_node_id == self.node_id), None)
        if not target_node:
            self.report({'ERROR'}, f"Node with ID {self.node_id} not found.")
            return {'CANCELLED'}

        target_socket = next((s for s in target_node.outputs if s.identifier == self.socket_identifier), None)
        if not target_socket:
            self.report({'ERROR'}, f"Socket with identifier {self.socket_identifier} not found on node {self.node_id}.")
            return {'CANCELLED'}

        # First, deactivate all other final active sockets
        for node in node_tree.nodes:
            for sock in node.outputs:
                if sock.is_final_active:
                    sock.is_final_active = False

        # Set the target as the new final active socket
        target_socket.is_final_active = True

        # Explicitly trigger the main execution function from the reconciler.
        # This ensures immediate feedback from the user's action.
        reconciler.trigger_execution(node_tree)
        
        self.report({'INFO'}, f"Set {target_node.name}.{target_socket.name} as active output and triggered sync.")

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




_all_operators = (
    FN_OT_activate_socket,
    FN_OT_write_file,
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
