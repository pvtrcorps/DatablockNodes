import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketSelection
from ..query_types import FNSelectionQuery

class FN_difference_selection(FNBaseNode, bpy.types.Node):
    """Subtracts Selection B from Selection A."""
    bl_idname = "FN_difference_selection"
    bl_label = "Difference Selection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketSelection', "Selection A")
        self.inputs.new('FNSocketSelection', "Selection B")
        self.outputs.new('FNSocketSelection', "Selection")

    def execute(self, **kwargs):
        query_a = kwargs.get("Selection A")
        query_b = kwargs.get("Selection B")

        if not query_a:
            return { self.outputs[0].identifier: None }
        if not query_b:
            return { self.outputs[0].identifier: query_a }

        new_raw_expression = f"({query_a.raw_expression}) and not ({query_b.raw_expression})"
        
        new_query = FNSelectionQuery(
            raw_expression=new_raw_expression,
            path_glob="*",
            filters=[{"type": "difference", "queries": [query_a, query_b]}]
        )

        return { self.outputs[0].identifier: new_query }
