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
        update=lambda self, context: (self.update_sockets(context), self._trigger_update(context))
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

    def update_hash(self, hasher):
        super().update_hash(hasher)
        hasher.update(self.data_type.encode())

        # Hash the dynamically added Data input
        if self.data_type != 'NONE':
            data_input = self.inputs.get('Data')
            if data_input and data_input.is_linked:
                pass
            elif data_input and hasattr(data_input, 'default_value'):
                hasher.update(str(data_input.default_value).encode())

    def execute(self, **kwargs):
        obj = kwargs.get(self.inputs['Object'].identifier)
        tree = kwargs.get('tree')

        if not obj or not isinstance(obj, bpy.types.Object):
            print(f"  - Warning: No valid object provided to {self.name}. Skipping.")
            return None

        new_data = None
        relationship_type = None

        if self.data_type != 'NONE':
            data_input_socket = self.inputs.get('Data')
            if data_input_socket:
                new_data = kwargs.get(data_input_socket.identifier)
                relationship_type = f"OBJECT_DATA_ASSIGN_{self.data_type}"
        
        if new_data and isinstance(new_data, bpy.types.ID):
            obj.data = new_data
            print(f"  - Set data of object '{obj.name}' to '{new_data.name}' ({type(new_data).__name__})")
            
            # Register relationship
            new_rel_item = tree.fn_relationships_map.add()
            new_rel_item.node_id = self.fn_node_id
            new_rel_item.source_uuid = uuid_manager.get_uuid(obj)
            new_rel_item.target_uuid = uuid_manager.get_uuid(new_data)
            new_rel_item.relationship_type = relationship_type
        else:
            # If no data is provided or data_type is NONE, set object.data to None and remove any existing relationship
            if obj.data is not None:
                print(f"  - Clearing data of object '{obj.name}'")
                obj.data = None
            
            # Remove any existing OBJECT_DATA_ASSIGN relationships for this object
            relationships_to_remove_indices = []
            for i, rel_item in enumerate(tree.fn_relationships_map):
                if rel_item.node_id == self.fn_node_id and rel_item.source_uuid == uuid_manager.get_uuid(obj) and rel_item.relationship_type.startswith("OBJECT_DATA_ASSIGN"):
                    relationships_to_remove_indices.append(i)
            
            for i in sorted(relationships_to_remove_indices, reverse=True):
                tree.fn_relationships_map.remove(i)

        return {self.outputs[0].identifier: obj}
