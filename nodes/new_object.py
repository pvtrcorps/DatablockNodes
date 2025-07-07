
import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketString, FNSocketObject, FNSocketMesh, FNSocketLight, FNSocketCamera
from .. import uuid_manager

_object_data_socket = {
    'EMPTY': None,
    'MESH': 'FNSocketMesh',
    'LIGHT': 'FNSocketLight',
    'CAMERA': 'FNSocketCamera',
}

class FN_new_object(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_object"
    bl_label = "New Object"

    obj_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('EMPTY', 'Empty', ''),
            ('MESH', 'Mesh', ''),
            ('LIGHT', 'Light', ''),
            ('CAMERA', 'Camera', ''),
        ],
        default='EMPTY',
        update=lambda self, context: self.update_sockets(context)
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        while self.inputs:
            self.inputs.remove(self.inputs[-1])
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        name_sock = self.inputs.new('FNSocketString', "Name")
        name_sock.default_value = "Object"

        if _object_data_socket[self.obj_type]:
            self.inputs.new(_object_data_socket[self.obj_type], "Data")

        self.outputs.new('FNSocketObject', "Object")

    def draw_buttons(self, context, layout):
        layout.prop(self, "obj_type", text="Type")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        object_name = kwargs.get(self.inputs['Name'].identifier, "Object")
        object_data = kwargs.get(self.inputs.get('Data', {}).get('identifier'))

        print(f"\n[FN_new_object] Node ID: {self.fn_node_id}")
        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        print(f"[FN_new_object] Map Item found: {map_item is not None}")
        
        existing_object = None
        if map_item:
            print(f"[FN_new_object] Map Item Datablock UUID: {map_item.datablock_uuid}")
            existing_object = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid)
        
        print(f"[FN_new_object] Existing object found: {existing_object is not None}")

        if existing_object:
            if existing_object.name != object_name:
                existing_object.name = object_name
                print(f"  - Updated object name to: '{existing_object.name}'")
            if object_data and existing_object.data != object_data:
                existing_object.data = object_data
                print(f"  - Updated object data for: '{existing_object.name}'")
            return existing_object
        else:
            def create_new_object():
                if self.obj_type == 'EMPTY':
                    return bpy.data.objects.new(name=object_name, object_data=None)
                elif self.obj_type == 'MESH':
                    data = object_data if isinstance(object_data, bpy.types.Mesh) else bpy.data.meshes.new(name=object_name + "_mesh")
                    return bpy.data.objects.new(name=object_name, object_data=data)
                elif self.obj_type == 'LIGHT':
                    data = object_data if isinstance(object_data, bpy.types.Light) else bpy.data.lights.new(name=object_name + "_light", type='POINT')
                    return bpy.data.objects.new(name=object_name, object_data=data)
                elif self.obj_type == 'CAMERA':
                    data = object_data if isinstance(object_data, bpy.types.Camera) else bpy.data.cameras.new(name=object_name + "_camera")
                    return bpy.data.objects.new(name=object_name, object_data=data)
                return None

            new_object = create_new_object()
            if new_object:
                uuid_manager.set_uuid(new_object)
                print(f"  - Created new Object: {new_object.name}")
                if map_item:
                    map_item.datablock_uuid = uuid_manager.get_uuid(new_object)
                else:
                    new_map_item = tree.fn_state_map.add()
                    new_map_item.node_id = self.fn_node_id
                    new_map_item.datablock_uuid = uuid_manager.get_uuid(new_object)
            return new_object
