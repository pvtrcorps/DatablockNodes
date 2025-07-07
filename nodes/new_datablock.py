import bpy
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketString, FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld
)
from .. import uuid_manager

_datablock_socket_map = {
    'SCENE': 'FNSocketScene',
    'OBJECT': 'FNSocketObject',
    'COLLECTION': 'FNSocketCollection',
    'CAMERA': 'FNSocketCamera',
    'IMAGE': 'FNSocketImage',
    'LIGHT': 'FNSocketLight',
    'MATERIAL': 'FNSocketMaterial',
    'MESH': 'FNSocketMesh',
    'NODETREE': 'FNSocketNodeTree',
    'TEXT': 'FNSocketText',
    'WORKSPACE': 'FNSocketWorkSpace',
    'WORLD': 'FNSocketWorld',
}

_datablock_creation_map = {
    'SCENE': lambda name: bpy.data.scenes.new(name=name),
    'OBJECT': lambda name, obj_type, object_data: (
        bpy.data.objects.new(name=name, object_data=None) if obj_type == 'EMPTY' else
        bpy.data.objects.new(name=name, object_data=object_data if isinstance(object_data, bpy.types.Mesh) else bpy.data.meshes.new(name=name + "_mesh")) if obj_type == 'MESH' else
        bpy.data.objects.new(name=name, object_data=object_data if isinstance(object_data, bpy.types.Light) else bpy.data.lights.new(name=name + "_light", type='POINT')) if obj_type == 'LIGHT' else
        bpy.data.objects.new(name=name, object_data=object_data if isinstance(object_data, bpy.types.Camera) else bpy.data.cameras.new(name=name + "_camera")) if obj_type == 'CAMERA' else
        None
    ),
    'COLLECTION': lambda name: bpy.data.collections.new(name=name),
    'CAMERA': lambda name: bpy.data.cameras.new(name=name),
    'IMAGE': lambda name, width, height: bpy.data.images.new(name=name, width=width, height=height),
    'LIGHT': lambda name, light_type: bpy.data.lights.new(name=name, type=light_type),
    'MATERIAL': lambda name: bpy.data.materials.new(name=name),
    'MESH': lambda name: bpy.data.meshes.new(name=name),
    'NODETREE': lambda name: bpy.data.node_groups.new(name=name, type='ShaderNodeTree'),
    'TEXT': lambda name: bpy.data.texts.new(name=name),
    'WORKSPACE': lambda name: bpy.data.workspaces.new(name=name),
    'WORLD': lambda name: bpy.data.worlds.new(name=name),
}

class FN_new_datablock(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_new_datablock"
    bl_label = "New Datablock"

    datablock_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('SCENE', 'Scene', ''),
            ('OBJECT', 'Object', ''),
            ('COLLECTION', 'Collection', ''),
            ('CAMERA', 'Camera', ''),
            ('IMAGE', 'Image', ''),
            ('LIGHT', 'Light', ''),
            ('MATERIAL', 'Material', ''),
            ('MESH', 'Mesh', ''),
            ('NODETREE', 'Node Tree', ''),
            ('TEXT', 'Text', ''),
            ('WORKSPACE', 'WorkSpace', ''),
            ('WORLD', 'World', ''),
        ],
        default='SCENE',
        update=lambda self, context: self.update_sockets(context)
    )

    obj_type: bpy.props.EnumProperty(
        name="Object Type",
        items=[
            ('EMPTY', 'Empty', ''),
            ('MESH', 'Mesh', ''),
            ('LIGHT', 'Light', ''),
            ('CAMERA', 'Camera', ''),
        ],
        default='EMPTY',
        update=lambda self, context: self.update_sockets(context)
    )

    light_type: bpy.props.EnumProperty(
        name="Light Type",
        items=[
            ('POINT', 'Point', ''),
            ('SUN', 'Sun', ''),
            ('SPOT', 'Spot', ''),
            ('AREA', 'Area', ''),
        ],
        default='POINT',
        update=lambda self, context: self.update_sockets(context)
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Name")
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear all existing sockets except 'Name' input
        for socket in list(self.inputs):
            if socket.identifier != "Name":
                self.inputs.remove(socket)
        while self.outputs:
            self.outputs.remove(self.outputs[-1])

        # Add specific input sockets based on datablock_type
        if self.datablock_type == 'OBJECT':
            _object_data_socket = {
                'EMPTY': None,
                'MESH': 'FNSocketMesh',
                'LIGHT': 'FNSocketLight',
                'CAMERA': 'FNSocketCamera',
            }
            if _object_data_socket[self.obj_type]:
                self.inputs.new(_object_data_socket[self.obj_type], "Data")
        elif self.datablock_type == 'IMAGE':
            self.inputs.new('FNSocketInt', "Width")
            self.inputs.new('FNSocketInt', "Height")
        elif self.datablock_type == 'LIGHT':
            pass # No special input sockets for light creation yet

        # Add main output socket based on selected type
        socket_type = _datablock_socket_map.get(self.datablock_type)
        if socket_type:
            self.outputs.new(socket_type, self.datablock_type.capitalize())

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")
        if self.datablock_type == 'OBJECT':
            layout.prop(self, "obj_type", text="Object Type")
        elif self.datablock_type == 'LIGHT':
            layout.prop(self, "light_type", text="Light Type")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        datablock_name = kwargs.get(self.inputs['Name'].identifier, self.datablock_type.capitalize())

        print(f"\n[FN_new_datablock] Node ID: {self.fn_node_id}")
        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
        print(f"[FN_new_datablock] Map Item found: {map_item is not None}")
        
        existing_datablock = None
        if map_item:
            print(f"[FN_new_datablock] Map Item Datablock UUID: {map_item.datablock_uuid}")
            existing_datablock = uuid_manager.find_datablock_by_uuid(map_item.datablock_uuid)
        
        print(f"[FN_new_datablock] Existing datablock found: {existing_datablock is not None}")

        if existing_datablock:
            if existing_datablock.name != datablock_name:
                existing_datablock.name = datablock_name
                print(f"  - Updated {self.datablock_type.lower()} name to: '{existing_datablock.name}'")
            return existing_datablock
        else:
            creation_func = _datablock_creation_map.get(self.datablock_type)
            if creation_func:
                new_datablock = None
                if self.datablock_type == 'OBJECT':
                    object_data = kwargs.get(self.inputs.get('Data', {}).get('identifier'))
                    new_datablock = creation_func(datablock_name, self.obj_type, object_data)
                elif self.datablock_type == 'IMAGE':
                    image_width = kwargs.get(self.inputs['Width'].identifier, 1024)
                    image_height = kwargs.get(self.inputs['Height'].identifier, 1024)
                    new_datablock = creation_func(datablock_name, image_width, image_height)
                elif self.datablock_type == 'LIGHT':
                    new_datablock = creation_func(datablock_name, self.light_type)
                else:
                    new_datablock = creation_func(datablock_name)
                uuid_manager.set_uuid(new_datablock)
                print(f"  - Created new {self.datablock_type.capitalize()}: {new_datablock.name}")

                if map_item:
                    map_item.datablock_uuid = uuid_manager.get_uuid(new_datablock)
                else:
                    new_map_item = tree.fn_state_map.add()
                    new_map_item.node_id = self.fn_node_id
                    new_map_item.datablock_uuid = uuid_manager.get_uuid(new_datablock)
                
                return new_datablock
            return None
