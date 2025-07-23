import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketSelection, FNSocketString
from ..engine import utils
from ..query_types import FNSelectionQuery

class FN_set_property(FNBaseNode, bpy.types.Node):
    """
    Finds prims in the scene graph using a Selection and sets or modifies their properties.
    """
    bl_idname = "FN_set_property"
    bl_label = "Set Property"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketSelection', "Selection")
        self.inputs.new('FNSocketString', "Property Name").default_value = "location"
        self.inputs.new('FNSocketString', "Value").default_value = "(0, 0, 0)"
        self.outputs.new('FNSocketScene', "Scene")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        selection_query = kwargs.get("Selection")
        prop_name = kwargs.get("Property Name")
        prop_value_str = kwargs.get("Value")

        if not scene_root or not prop_name:
            return {self.outputs[0].identifier: scene_root}

        # If no selection is provided, create a query that selects everything.
        if not selection_query:
            selection_query = FNSelectionQuery(raw_expression="*", path_glob="*", filters=[])

        # Clone the scene to work on a copy
        new_scene_root = scene_root.clone()

        # Resolve the selection to get the target prims
        target_prims = utils.resolve_selection(new_scene_root, selection_query)

        # Try to evaluate the property value from the string
        try:
            evaluated_value = eval(prop_value_str)
        except:
            evaluated_value = prop_value_str

        for prim in target_prims:
            # The property name is now used directly.
            prim.properties[prop_name] = evaluated_value

        return {self.outputs[0].identifier: new_scene_root}