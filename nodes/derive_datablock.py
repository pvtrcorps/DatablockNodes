



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
            source_socket = self.inputs.new(socket_type, "Source")
            source_socket.is_mutable = False # Set to False to prevent implicit copying
            self.outputs.new(socket_type, "Derived")
        
        self.inputs.new('FNSocketString', "Name")

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")

    

    def execute(self, **kwargs):
        source_uuid = kwargs.get(self.inputs['Source'].identifier)
        new_name = kwargs.get(self.inputs['Name'].identifier)
        print(f"[FN_DEBUG] Derive Datablock: Received source_uuid = {source_uuid} (Type: {type(source_uuid).__name__})")

        if not source_uuid:
            # If no source, declare an empty state for this node's output
            return {self.outputs['Derived'].identifier: None, 'states': {self.fn_node_id: ""}}

        # Generate a new UUID for the derived datablock.
        # The reconciler will handle the actual copying and naming.
        derived_uuid = uuid_manager.generate_uuid()

        # Declare the intention to derive a datablock
        # The reconciler will use this to manage the actual Blender datablocks
        return {
            self.outputs['Derived'].identifier: derived_uuid,
            'declarations': {
                'derive_datablock': {
                    'source_uuid': source_uuid,
                    'derived_uuid': derived_uuid,
                    'new_name': new_name
                }
            },
            'states': {
                self.fn_node_id: f"{source_uuid},{derived_uuid}"
            }
        }



