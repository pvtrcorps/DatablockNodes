import bpy
from .engine import orchestrator

def _activate_upstream(node):
    """Recursively activate all sockets and nodes upstream from the given node."""
    for sock in node.inputs:
        if hasattr(sock, 'is_active'):
            sock.is_active = True
        if sock.is_linked:
            # Also activate the output socket on the other side of the connection
            other_sock = sock.links[0].from_socket
            if hasattr(other_sock, 'is_active'):
                other_sock.is_active = True
            _activate_upstream(sock.links[0].from_node)

class FN_OT_activate_socket(bpy.types.Operator):
    """Activates a socket, sets it as the final execution point, and triggers sync."""
    bl_idname = "fn.activate_socket"
    bl_label = "Activate and Sync Socket"

    node_id: bpy.props.StringProperty()
    socket_identifier: bpy.props.StringProperty()

    def execute(self, context):
        tree = context.space_data.edit_tree
        if not tree:
            return {'CANCELLED'}

        target_node = next((n for n in tree.nodes if hasattr(n, 'fn_node_id') and n.fn_node_id == self.node_id), None)
        if not target_node:
            return {'CANCELLED'}

        target_socket = next((s for s in target_node.outputs if s.identifier == self.socket_identifier), None)
        if not target_socket:
            return {'CANCELLED'}

        # --- Full State Reset ---
        # Deactivate all sockets (inputs and outputs) across the entire tree first.
        for node in tree.nodes:
            for sock in node.inputs:
                if hasattr(sock, 'is_active'):
                    sock.is_active = False
                if hasattr(sock, 'is_final_active'):
                    sock.is_final_active = False
            for sock in node.outputs:
                if hasattr(sock, 'is_active'):
                    sock.is_active = False
                if hasattr(sock, 'is_final_active'):
                    sock.is_final_active = False

        # --- Activate the Final Socket ---
        target_socket.is_final_active = True
        target_socket.is_active = True # The final socket is also part of the active chain

        # --- Activate the Upstream Visual Trail ---
        _activate_upstream(target_node)

        # --- Trigger Execution ---
        depsgraph = context.evaluated_depsgraph_get()
        orchestrator.execute_node_tree(tree, depsgraph)
        
        return {'FINISHED'}

class FN_OT_clear_overrides(bpy.types.Operator):
    """Clears all user overrides from the active node tree."""
    bl_idname = "fn.clear_overrides"
    bl_label = "Clear All User Overrides"
    bl_description = "Removes all stored user overrides from this node tree, reverting all datablocks to the state defined by the nodes"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        tree = getattr(context.space_data, "edit_tree", None)
        return tree and tree.bl_idname == 'DatablockTreeType'

    def execute(self, context):
        tree = context.space_data.edit_tree
        
        if not hasattr(tree, 'fn_override_map'):
            self.report({'WARNING'}, "Active node tree does not support overrides.")
            return {'CANCELLED'}

        if not tree.fn_override_map:
            self.report({'INFO'}, "No overrides to clear.")
            return {'CANCELLED'}

        override_count = len(tree.fn_override_map)
        tree.fn_override_map.clear()

        # Trigger a scene update by tagging the tree
        tree.update_tag()
        
        # Force a depsgraph update for immediate visual feedback
        depsgraph = context.evaluated_depsgraph_get()
        orchestrator.execute_node_tree(tree, depsgraph)

        self.report({'INFO'}, f"Cleared {override_count} user overrides.")
        return {'FINISHED'}

_all_operators = (
    FN_OT_activate_socket,
    FN_OT_clear_overrides,
)

def register():
    for cls in _all_operators:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(_all_operators):
        bpy.utils.unregister_class(cls)
