import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketSelection
from ..query_types import FNSelectionQuery

class FN_union_selection(FNBaseNode, bpy.types.Node):
    """Combines multiple selections into a single selection (Union)."""
    bl_idname = "FN_union_selection"
    bl_label = "Union Selection"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketSelection', "Selection A")
        self.inputs.new('FNSocketSelection', "Selection B")
        self.outputs.new('FNSocketSelection', "Selection")

    def execute(self, **kwargs):
        query_a = kwargs.get("Selection A")
        query_b = kwargs.get("Selection B")

        if not query_a and not query_b:
            return { self.outputs[0].identifier: None }
        if not query_a:
            return { self.outputs[0].identifier: query_b }
        if not query_b:
            return { self.outputs[0].identifier: query_a }

        # Combine the expressions with an "or" operator
        new_raw_expression = f"({query_a.raw_expression}) or ({query_b.raw_expression})"
        
        # The parser in the Select node would need to be updated to handle this.
        # For now, we create a new query object that represents this union.
        # A more robust resolver would handle this combined query.
        # This is a simplified representation for now.
        new_query = FNSelectionQuery(
            raw_expression=new_raw_expression,
            path_glob="*", # A combined query might have multiple paths
            filters=[{"type": "union", "queries": [query_a, query_b]}] # Special filter type
        )

        return { self.outputs[0].identifier: new_query }
