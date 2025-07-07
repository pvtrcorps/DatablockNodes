"""Operators for the File Nodes addon."""

import bpy
from . import reconciler

class FN_OT_evaluate_all(bpy.types.Operator):
    """Evaluates the active File Nodes tree."""
    bl_idname = "fn.evaluate_all"
    bl_label = "Evaluate Node Tree"

    @classmethod
    def poll(cls, context):
        return isinstance(context.space_data.edit_tree, bpy.types.NodeTree)

    def execute(self, context):
        reconciler.execute_tree(context.space_data.edit_tree)
        return {'FINISHED'}

class FN_OT_recreate_node_setup(bpy.types.Operator):
    """Recreates the current node setup in the active File Nodes tree."""
    bl_idname = "fn.recreate_node_setup"
    bl_label = "Recreate Node Setup"

    @classmethod
    def poll(cls, context):
        return isinstance(context.space_data.edit_tree, bpy.types.NodeTree)

    def execute(self, context):
        tree = context.space_data.edit_tree
        if not tree:
            self.report({'WARNING'}, "No active node tree found.")
            return {'CANCELLED'}

        self.report({'INFO'}, "Recreating node setup...")

        # 1. Store current node setup
        node_data = []
        link_data = []

        # Store nodes and their basic properties
        for node in tree.nodes:
            node_info = {
                'bl_idname': node.bl_idname,
                'name': node.name,
                'location': (node.location.x, node.location.y),
                'fn_node_id': getattr(node, 'fn_node_id', ''),
                'properties': {}
            }
            # Store input socket values if not linked and has a 'value' attribute
            for input_socket in node.inputs:
                if not input_socket.is_linked and hasattr(input_socket, 'value'):
                    node_info['properties'][input_socket.identifier] = input_socket.value
            node_data.append(node_info)

        # Store links
        for link in tree.links:
            link_info = {
                'from_node_name': link.from_node.name,
                'from_socket_identifier': link.from_socket.identifier,
                'to_node_name': link.to_node.name,
                'to_socket_identifier': link.to_socket.identifier,
            }
            link_data.append(link_info)

        # 2. Clear existing nodes
        tree.nodes.clear()

        # 3. Recreate nodes
        # Create a mapping from old node names to new node instances
        new_nodes_map = {}
        for node_info in node_data:
            new_node = tree.nodes.new(node_info['bl_idname'])
            new_node.name = node_info['name']
            new_node.location = node_info['location']
            

            # Restore input socket values
            for prop_id, prop_value in node_info['properties'].items():
                if prop_id in new_node.inputs:
                    new_node.inputs[prop_id].value = prop_value

            new_nodes_map[node_info['name']] = new_node

        # 4. Recreate links
        for link_info in link_data:
            from_node = new_nodes_map.get(link_info['from_node_name'])
            to_node = new_nodes_map.get(link_info['to_node_name'])

            if from_node and to_node:
                from_socket = from_node.outputs.get(link_info['from_socket_identifier'])
                to_socket = to_node.inputs.get(link_info['to_socket_identifier'])

                if from_socket and to_socket:
                    tree.links.new(from_socket, to_socket)
                else:
                    self.report({'WARNING'}, f"Could not find sockets for link: {link_info}")
            else:
                self.report({'WARNING'}, f"Could not find nodes for link: {link_info}")

        self.report({'INFO'}, "Node setup recreated successfully.")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(FN_OT_evaluate_all)
    bpy.utils.register_class(FN_OT_recreate_node_setup)

def unregister():
    bpy.utils.unregister_class(FN_OT_evaluate_all)
    bpy.utils.unregister_class(FN_OT_recreate_node_setup)