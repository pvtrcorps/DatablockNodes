import bpy
import re
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketSelection, FNSocketString
from ..query_types import FNSelectionQuery

class FN_select(FNBaseNode, bpy.types.Node):
    """Selects prims in the scene graph based on a powerful expression."""
    bl_idname = "FN_select"
    bl_label = "Select"

    expression: bpy.props.StringProperty(
        name="Expression", 
        default="/root/*",
        update=lambda s,c: s.id_data.update_tag()
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Expression")
        self.outputs.new('FNSocketSelection', "Selection")

    def execute(self, **kwargs):
        expr_str = kwargs.get("Expression") or self.expression
        query = self.parse_expression(expr_str)
        return { self.outputs[0].identifier: query }

    def parse_expression(self, expr: str) -> FNSelectionQuery:
        """Parses the user expression into a structured query object based on DNSelect syntax."""
        raw_expression = expr
        path_glob = ""
        filters = []

        # Corrected Regex: `[^]]` to correctly match 'not a closing bracket'.
        match = re.match(r"\s*(?P<path>[^\[]+)?\s*(\[(?P<filters>[^]]+)\])?", expr)
        
        if not match:
            return FNSelectionQuery(raw_expression=raw_expression, path_glob=expr, filters=[])

        path_part = match.group('path')
        filter_part = match.group('filters')

        path_glob = path_part.strip() if path_part else "//**/*"

        if filter_part:
            filter_strings = [f.strip() for f in filter_part.split('and')]
            for f_str in filter_strings:
                func_match = re.match(r"(\w+)\s*\(\s*['\"](\w+)['\"]\s*\)", f_str)
                if func_match:
                    filters.append({
                        'type': 'function',
                        'func': func_match.group(1),
                        'value': func_match.group(2)
                    })
                    continue
                
                prop_match = re.match(r"@([\w\.]+)\s*([=<>!]+)\s*(.+)", f_str)
                if prop_match:
                    filters.append({
                        'type': 'property',
                        'key': prop_match.group(1),
                        'op': prop_match.group(2),
                        'value': prop_match.group(3).strip()
                    })

        return FNSelectionQuery(
            raw_expression=raw_expression,
            path_glob=path_glob,
            filters=filters
        )