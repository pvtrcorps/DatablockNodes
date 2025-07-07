import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketObject, FNSocketString

class FN_set_object_name(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_object_name"
    bl_label = "Set Object Name"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketObject', "Object")
        self.inputs.new('FNSocketString', "New Name")
        self.outputs.new('FNSocketObject', "Object")

    def execute(self, **kwargs):
        input_object = kwargs.get(self.inputs['Object'].identifier)
        new_name = kwargs.get(self.inputs['New Name'].identifier)

        if not input_object:
            print(f"  - Warning: No input object provided to {self.name}. Skipping.")
            return None

        if new_name is None:
            print(f"  - Warning: No new name provided to {self.name}. Skipping.")
            return input_object # Return object unmodified

        input_object.name = new_name
        print(f"  - Set object name to: '{input_object.name}'")

        return input_object
