import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketSceneList, FNSocketPulse
from ..engine import orchestrator

class FN_batch_render(FNBaseNode, bpy.types.Node):
    """
    An executor node that takes a list of scenes, materializes each one sequentially,
    renders it, and then destroys it to free memory.
    """
    bl_idname = "FN_batch_render"
    bl_label = "Batch Render"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketSceneList', "Scene List")
        # A pulse input to trigger the execution
        self.inputs.new('FNSocketPulse', "Execute")
        self.outputs.new('FNSocketPulse', "Finished")

    def execute(self, **kwargs):
        # This node doesn't run during normal evaluation. It's triggered by an operator.
        # The actual logic will be in an operator that calls a function in this module.
        # For now, the execute function does nothing.
        return {self.outputs[0].identifier: True}

# We need an operator to run the batch process, as it's a modal operation
# that needs to control the application state directly.

class FN_OT_run_batch_render(bpy.types.Operator):
    """Runs the batch render process for a given node."""
    bl_idname = "fn.run_batch_render"
    bl_label = "Run Batch Render"

    node_id: bpy.props.StringProperty()

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        target_node = next((n for n in node_tree.nodes if n.fn_node_id == self.node_id), None)
        if not target_node:
            self.report({'ERROR'}, "Target node not found.")
            return {'CANCELLED'}

        # 1. Evaluate the graph to get the list of scene roots
        scene_list_socket = target_node.inputs["Scene List"]
        if not scene_list_socket.is_linked:
            self.report({'ERROR'}, "Scene List input is not connected.")
            return {'CANCELLED'}
        
        # We need a temporary evaluation to get the list
        # This is a simplified version of the main orchestrator logic
        session_cache = {}
        upstream_results = orchestrator._evaluate_node(node_tree, scene_list_socket.links[0].from_node, session_cache)
        scene_list = upstream_results.get(scene_list_socket.links[0].from_socket.identifier, [])

        if not scene_list:
            self.report({'WARNING'}, "Input scene list is empty.")
            return {'FINISHED'}

        # 2. Iterate and render each scene
        for i, scene_root in enumerate(scene_list):
            self.report({'INFO'}, f"Processing scene {i+1}/{len(scene_list)}: {scene_root.path}")
            
            # a. Materialize the scene
            plan = orchestrator.planner.plan_execution(scene_root)
            orchestrator._synchronize_blender_state(node_tree, plan, context.evaluated_depsgraph_get())
            
            # b. Set the active scene and render
            # We need to find the materialized scene datablock
            scene_db = orchestrator.uuid_manager.find_datablock_by_uuid(str(scene_root.fn_uuid))
            if scene_db:
                context.window.scene = scene_db
                bpy.ops.render.render(write_still=True)
            else:
                self.report({'ERROR'}, f"Could not find materialized scene for {scene_root.path}")

            # c. Clean up (destroy the scene) before the next iteration
            orchestrator._synchronize_blender_state(node_tree, [], context.evaluated_depsgraph_get())

        self.report({'INFO'}, "Batch render finished.")
        return {'FINISHED'}

# The node itself needs a button to call the operator

def add_render_button(self, context, layout):
    op = layout.operator("fn.run_batch_render", text="Run Batch Render")
    op.node_id = self.fn_node_id

# We need to register the operator and add the button to the node's draw function

_classes = (FN_batch_render, FN_OT_run_batch_render)

def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    FN_batch_render.draw_buttons = add_render_button

def unregister():
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
