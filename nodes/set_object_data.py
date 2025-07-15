import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketObject, FNSocketMesh, FNSocketArmature, FNSocketLight, FNSocketCamera

_data_socket_map = {
    'NONE': None,
    'MESH': 'FNSocketMesh',
    'ARMATURE': 'FNSocketArmature',
    'LIGHT': 'FNSocketLight',
    'CAMERA': 'FNSocketCamera',
}

def _update_node(self, context):
    self.update_sockets(context)
    self._trigger_update(context)

class FN_set_object_data(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_object_data"
    bl_label = "Set Object Data"

    data_type: bpy.props.EnumProperty(
        name="Data Type",
        items=[
            ('NONE', 'None', 'Clear object data'),
            ('MESH', 'Mesh', 'Assign Mesh data'),
            ('ARMATURE', 'Armature', 'Assign Armature data'),
            ('LIGHT', 'Light', 'Assign Light data'),
            ('CAMERA', 'Camera', 'Assign Camera data'),
        ],
        default='NONE',
        update=_update_node
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketObject', "Object").is_mutable = True
        self.outputs.new('FNSocketObject', "Object")
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear all existing data input sockets
        for socket in list(self.inputs):
            if socket.identifier != "Object":
                self.inputs.remove(socket)
        
        # Add specific input socket based on data_type
        socket_type = _data_socket_map.get(self.data_type)
        if socket_type:
            self.inputs.new(socket_type, "Data")

    def draw_buttons(self, context, layout):
        layout.prop(self, "data_type", text="Data Type")

    

    def execute(self, **kwargs):
        obj_uuid = kwargs.get(self.inputs['Object'].identifier)
        new_data_uuid = kwargs.get(self.inputs['Data'].identifier) if self.data_type != 'NONE' else None
        assignments = []

        if obj_uuid:
            assignments.append({
                'target_uuid': obj_uuid,
                'property_name': 'data',
                'value_uuid': new_data_uuid if new_data_uuid else ''
            })

        return {
            self.outputs[0].identifier: obj_uuid,
            'property_assignments': assignments
        }