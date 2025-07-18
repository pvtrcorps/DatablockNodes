import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketStringList

class FN_split_string(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_split_string"
    bl_label = "Split String"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.manages_scene_datablock = False
        self.inputs.new('FNSocketString', "Separator")
        self.inputs.new('FNSocketString', "String")
        output_socket = self.outputs.new('FNSocketStringList', "List")
        output_socket.display_shape = 'SQUARE'

    def draw_buttons(self, context, layout):
        pass

    def execute(self, **kwargs):
        input_string = kwargs.get(self.inputs['String'].identifier, "")
        separator = kwargs.get(self.inputs['Separator'].identifier, " ") # Default to space if no separator

        if not input_string:
            return {self.outputs['List'].identifier: []}

        return {self.outputs['List'].identifier: input_string.split(separator)}
