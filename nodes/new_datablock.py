import bpy
import json
from ..nodes.base import FNBaseNode
from ..sockets import (
    FNSocketString, FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld
)
from .. import uuid_manager
from ..properties import _datablock_socket_map, _datablock_creation_map

def _update_node(self, context):
    self.update_sockets(context)
    self._trigger_update(context)

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
        update=_update_node
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
        update=_update_node
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
        
        output_socket_identifier = self.outputs[0].identifier
        state_id = f"{self.fn_node_id}:{output_socket_identifier}"

        # --- Declarations ---
        # This node is now purely declarative. It doesn't modify anything directly.
        # It declares the *intent* to have a datablock, and provides the necessary
        # parameters for the reconciler to create it.

        # Prepare creation parameters based on datablock type
        creation_params = {
            'type': self.datablock_type,
            'uuid': self.fn_output_uuid # The UUID this node declares for its output datablock
        }

        if self.datablock_type == 'IMAGE':
            creation_params['width'] = kwargs.get(self.inputs['Width'].identifier, 1024)
            creation_params['height'] = kwargs.get(self.inputs['Height'].identifier, 1024)
        elif self.datablock_type == 'LIGHT':
            creation_params['light_type'] = self.light_type
        
        # 1. Declare the assignment of the name property.
        assignments = [{
            'target_uuid': self.fn_output_uuid,
            'property_name': 'name',
            'value_type': 'LITERAL',
            'value_uuid': '', # Not used for literals
            'value_json': json.dumps(datablock_name)
        }]

        # 2. Declare the state (which datablock this node is responsible for).
        # The 'output_socket_identifier' will now hold the creation declaration,
        # not a bpy.types.ID object directly.
        return_dict = {
            output_socket_identifier: self.fn_output_uuid, # Pass only the UUID
            'states': {
                state_id: self.fn_output_uuid # Still declare the UUID for the state map
            },
            'property_assignments': assignments,
            'declarations': {
                'create_datablock': creation_params # Declare the creation intent separately
            }
        }
        print(f"[FN_DEBUG] New Datablock: Returning {return_dict[output_socket_identifier]} for socket {output_socket_identifier}")
        return return_dict