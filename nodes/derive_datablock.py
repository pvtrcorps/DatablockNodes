



import bpy
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketString, FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld, FNSocketArmature, FNSocketAction
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

def _update_node(self, context):
    self.update_sockets(context)
    self._trigger_update(context)

class FN_derive_datablock(FNBaseNode, bpy.types.Node):
    """Creates a managed, explicit copy of a datablock based on the input."""
    bl_idname = "FN_derive_datablock"
    bl_label = "Derive Datablock"

    datablock_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('SCENE', 'Scene', 'Derive a Scene'),
            ('OBJECT', 'Object', 'Derive an Object'),
            ('COLLECTION', 'Collection', 'Derive a Collection'),
            ('MATERIAL', 'Material', 'Derive a Material'),
            ('MESH', 'Mesh', 'Derive a Mesh'),
            ('LIGHT', 'Light', 'Derive a Light'),
            ('CAMERA', 'Camera', 'Derive a Camera'),
            ('IMAGE', 'Image', 'Derive an Image'),
            ('NODETREE', 'Node Tree', 'Derive a Node Tree'),
            ('TEXT', 'Text', 'Derive a Text Block'),
            ('WORLD', 'World', 'Derive a World'),
            ('ARMATURE', 'Armature', 'Derive an Armature'),
            ('ACTION', 'Action', 'Derive an Action'),
        ],
        default='OBJECT',
        update=_update_node
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        for socket in list(self.inputs):
            self.inputs.remove(socket)
        for socket in list(self.outputs):
            self.outputs.remove(socket)

        socket_type = _datablock_socket_map.get(self.datablock_type)
        if socket_type:
            self.inputs.new(socket_type, "Source")
            self.outputs.new(socket_type, "Derived")
        
        self.inputs.new('FNSocketString', "Name")

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")

    def update_hash(self, hasher):
        pass # No internal properties that affect the output

    def execute(self, **kwargs):
        tree = kwargs.get('tree')
        source_datablock = kwargs.get(self.inputs['Source'].identifier)
        new_name = kwargs.get(self.inputs['Name'].identifier)

        if not source_datablock:
            # Clear the state if the source is disconnected
            map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)
            if map_item:
                map_item.datablock_uuids = ""
            return {}

        output_socket_identifier = self.outputs['Derived'].identifier
        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id), None)

        managed_copy = None
        previous_source_uuid = None

        if map_item and map_item.datablock_uuids:
            uuids = map_item.datablock_uuids.split(',')
            if len(uuids) == 2:
                previous_source_uuid = uuids[0]
                managed_copy = uuid_manager.find_datablock_by_uuid(uuids[1])

        current_source_uuid = uuid_manager.get_or_create_uuid(source_datablock)

        should_create_new_copy = not managed_copy or current_source_uuid != previous_source_uuid

        if should_create_new_copy:
            print(f"[Derive Node] Source changed or no copy exists. Deriving new copy from '{source_datablock.name}'.")
            new_copy = source_datablock.copy()
            uuid_manager.set_uuid(new_copy, force_new=True)
            new_copy_uuid = uuid_manager.get_uuid(new_copy)

            if new_name:
                new_copy.name = new_name
            
            if not map_item:
                map_item = tree.fn_state_map.add()
                map_item.node_id = self.fn_node_id
            
            map_item.datablock_uuids = f"{current_source_uuid},{new_copy_uuid}"
            
            return {output_socket_identifier: new_copy}
        else:
            print(f"[Derive Node] Reusing existing managed copy '{managed_copy.name}'.")
            if new_name and managed_copy.name != new_name:
                managed_copy.name = new_name
            
            return {output_socket_identifier: managed_copy}



