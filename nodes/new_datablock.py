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
    'ARMATURE': 'FNSocketArmature',
    'ACTION': 'FNSocketAction',
}

_datablock_creation_map = {
    'SCENE': lambda name: bpy.data.scenes.new(name=name),
    'OBJECT': lambda name: bpy.data.objects.new(name=name, object_data=None), # Simplified: always create generic object
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
    'ARMATURE': lambda name: bpy.data.armatures.new(name=name),
    'ACTION': lambda name: bpy.data.actions.new(name=name),
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
            ('ARMATURE', 'Armature', ''),
            ('ACTION', 'Action', ''),
        ],
        default='SCENE',
        update=lambda self, context: (self.update_sockets(context), self._trigger_update(context))
    )

    # Removed obj_type as it's no longer directly used for data creation here

    light_type: bpy.props.EnumProperty(
        name="Light Type",
        items=[
            ('POINT', 'Point', ''),
            ('SUN', 'Sun', ''),
            ('SPOT', 'Spot', ''),
            ('AREA', 'Area', ''),
        ],
        default='POINT',
        update=lambda self, context: (self.update_sockets(context), self._trigger_update(context))
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
        # Removed 'OBJECT' specific input for 'Data'
        if self.datablock_type == 'IMAGE':
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
        # Removed obj_type from draw_buttons
        if self.datablock_type == 'LIGHT':
            layout.prop(self, "light_type", text="Light Type")

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        datablock_name = kwargs.get(self.inputs['Name'].identifier, self.datablock_type.capitalize())
        print(f"[FN_new_datablock] Debug: datablock_name before creation: '{datablock_name}' (Type: {type(datablock_name)})")

        print(f"\n[FN_new_datablock] Node ID: {self.fn_node_id})")
        output_socket_identifier = self.outputs[0].identifier
        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id and item.socket_identifier == output_socket_identifier), None)
        print(f"[FN_new_datablock] Map Item found: {map_item is not None}")
        
        existing_datablock = None
        if map_item and map_item.datablock_uuids:
            # A New Datablock node should only manage one datablock, so we take the first UUID
            existing_uuid = map_item.datablock_uuids.split(',')[0]
            existing_datablock = uuid_manager.find_datablock_by_uuid(existing_uuid)
        
        print(f"[FN_new_datablock] Existing datablock found: {existing_datablock is not None}")

        if existing_datablock:
            if existing_datablock.name != datablock_name:
                existing_datablock.name = datablock_name
                print(f"  - Updated {self.datablock_type.lower()} name to: '{existing_datablock.name}'")
            return {self.outputs[0].identifier: existing_datablock}
        else:
            creation_func = _datablock_creation_map.get(self.datablock_type)
            if creation_func:
                new_datablock = None
                if self.datablock_type == 'OBJECT':
                    new_datablock = creation_func(datablock_name) # Simplified call
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

                # Update fn_state_map with the new datablock's UUID, associated with the output socket
                output_socket_identifier = self.outputs[0].identifier
                found_map_item = False
                for item in tree.fn_state_map:
                    if item.node_id == self.fn_node_id and item.socket_identifier == output_socket_identifier:
                        item.datablock_uuids = uuid_manager.get_uuid(new_datablock)
                        found_map_item = True
                        break
                
                if not found_map_item:
                    new_map_item = tree.fn_state_map.add()
                    new_map_item.node_id = self.fn_node_id
                    new_map_item.socket_identifier = output_socket_identifier
                    new_map_item.datablock_uuids = uuid_manager.get_uuid(new_datablock)
                
                return {output_socket_identifier: new_datablock}
            return {}
