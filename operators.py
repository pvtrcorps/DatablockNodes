import bpy
from .engine import orchestrator

class FN_OT_activate_socket(bpy.types.Operator):
    """Activates a socket, sets it as the final execution point, and triggers sync."""
    bl_idname = "fn.activate_socket"
    bl_label = "Activate and Sync Socket"

    node_id: bpy.props.StringProperty()
    socket_identifier: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        
        target_node = next((n for n in node_tree.nodes if n.fn_node_id == self.node_id), None)
        if not target_node:
            return {'CANCELLED'}

        target_socket = next((s for s in target_node.outputs if s.identifier == self.socket_identifier), None)
        if not target_socket:
            return {'CANCELLED'}

        for node in node_tree.nodes:
            for sock in node.outputs:
                sock.is_final_active = False

        target_socket.is_final_active = True

        depsgraph = context.evaluated_depsgraph_get()
        orchestrator.execute_node_tree(node_tree, depsgraph)
        
        return {'FINISHED'}

_all_operators = (
    FN_OT_activate_socket,
)

def register():
    for cls in _all_operators:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(_all_operators):
        bpy.utils.unregister_class(cls)