import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..engine import utils, query_engine
from .. import logger

class FN_set_property(FNBaseNode, bpy.types.Node):
    """
    Finds proxies in the scene graph using a query and sets or modifies their properties.
    """
    bl_idname = "FN_set_property"
    bl_label = "Set Property"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketString', "Selection").default_value = "*"
        self.inputs.new('FNSocketString', "Property Name").default_value = "location"
        self.inputs.new('FNSocketString', "Value").default_value = "[0, 0, 0]"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        selection_string = kwargs.get("Selection")
        prop_name = kwargs.get("Property Name")
        prop_value_str = kwargs.get("Value")

        logger.log(f"Executing with: Scene={scene_root.path if scene_root else 'None'}, Selection='{selection_string}', Property='{prop_name}', Value='{prop_value_str}'")

        if not scene_root or not prop_name or not selection_string:
            logger.log("Missing required inputs. Returning original scene.", level='WARNING')
            return {self.outputs[0].identifier: scene_root}

        # Clone the scene to work on a copy
        new_scene_root = scene_root.clone()
        logger.log(f"Cloned scene root: {new_scene_root.path}")

        # Use the new query engine to get the target proxies
        selected_proxies = query_engine.execute_query(new_scene_root, selection_string)
        logger.log(f"Query '{selection_string}' returned {len(selected_proxies)} proxies.")

        # Try to evaluate the property value from the string
        try:
            # Using eval is a security risk, but necessary for user-defined tuples/lists.
            # In a real-world scenario, this should be replaced with a safer parser.
            evaluated_value = eval(prop_value_str)
            logger.log(f"Evaluated value: {evaluated_value} (type: {type(evaluated_value)})")
        except Exception as e:
            evaluated_value = prop_value_str
            logger.log(f"Could not evaluate value string '{prop_value_str}'. Using as-is. Error: {e}", level='WARNING')

        # Set the property on all selected proxies
        logger.log(f"Setting property '{prop_name}' on {len(selected_proxies)} proxies.")
        for proxy in selected_proxies:
            logger.log(f"  - Setting '{prop_name}' to '{evaluated_value}' on proxy: {proxy.path}")
            # Use the safe nested property setter
            utils.set_nested_property(proxy.properties, prop_name, evaluated_value)

        logger.log("Execution finished. Returning new scene root.")
        return {self.outputs[0].identifier: new_scene_root}
