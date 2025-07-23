import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketSelection
from ..query_types import FNSelectionQuery

class FN_intersection_selection(FNBaseNode, bpy.types.Node):
    """Combines two selections, resulting in their intersection."""
    bl_idname = "FN_intersection_selection"
    bl_label = "Intersection Selection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketSelection', "Selection A")
        self.inputs.new('FNSocketSelection', "Selection B")
        self.outputs.new('FNSocketSelection', "Selection")

    def execute(self, **kwargs):
        query_a = kwargs.get("Selection A")
        query_b = kwargs.get("Selection B")

        if not query_a or not query_b:
            return { self.outputs[0].identifier: None }

        new_raw_expression = f"({query_a.raw_expression}) and ({query_b.raw_expression})"
        
        new_query = FNSelectionQuery(
            raw_expression=new_raw_expression,
            path_glob="*",
            filters=[{"type": "intersection", "queries": [query_a, query_b]}]
        )

        return { self.outputs[0].identifier: new_query }
