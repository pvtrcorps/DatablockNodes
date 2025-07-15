
import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import (
    FNSocketObject, FNSocketCollection, FNSocketScene, FNSocketWorld, FNSocketCamera,
    FNSocketMesh, FNSocketLight, FNSocketMaterial, FNSocketObjectList, FNSocketCollectionList,
    FNSocketMaterialList
)
from .. import logger

# Maps the input datablock type to its corresponding socket type
_input_socket_map = {
    'OBJECT': 'FNSocketObject',
    'COLLECTION': 'FNSocketCollection',
    'SCENE': 'FNSocketScene',
}

# Defines the outputs for each type of input datablock
_output_map = {
    'OBJECT': {
        "Object Data": 'FNSocketMesh', # Simplified to Mesh for now
        "Materials": 'FNSocketMaterialList',
        "Parent": 'FNSocketObject',
        "Children": 'FNSocketObjectList',
    },
    'COLLECTION': {
        "Objects": 'FNSocketObjectList',
        "Child Collections": 'FNSocketCollectionList',
    },
    'SCENE': {
        "Master Collection": 'FNSocketCollection',
        "World": 'FNSocketWorld',
        "Active Camera": 'FNSocketCamera',
    },
}

def _update_node(self, context):
    self.update_sockets(context)
    self._trigger_update(context)

class FN_get_datablock_content(FNBaseNode, bpy.types.Node):
    """Inspects a datablock and exposes its content and properties."""
    bl_idname = "FN_get_datablock_content"
    bl_label = "Get Datablock Content"

    # Enum to select the type of datablock to inspect
    datablock_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('SCENE', 'Scene', 'Get content from a Scene'),
            ('COLLECTION', 'Collection', 'Get content from a Collection'),
            ('OBJECT', 'Object', 'Get content from an Object'),
        ],
        default='COLLECTION',
        update=_update_node
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        """Dynamically set the input and output sockets based on the selected type."""
        # Clear existing sockets
        for socket in list(self.inputs) + list(self.outputs):
            if socket.is_output:
                self.outputs.remove(socket)
            else:
                self.inputs.remove(socket)

        # Set the input socket
        input_socket_type = _input_socket_map.get(self.datablock_type)
        if input_socket_type:
            self.inputs.new(input_socket_type, "Source")

        # Set the output sockets
        outputs_for_type = _output_map.get(self.datablock_type, {})
        for label, socket_type in outputs_for_type.items():
            new_socket = self.outputs.new(socket_type, label)
            # Set the display shape to SQUARE for list types for UI consistency
            if 'List' in socket_type:
                new_socket.display_shape = 'SQUARE'

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")

    

    def execute(self, **kwargs):
        source_uuid = kwargs.get(self.inputs['Source'].identifier)

        if not source_uuid:
            return {}

        source_datablock = uuid_manager.find_datablock_by_uuid(source_uuid)

        if not source_datablock:
            logger.log(f"[FN_get_datablock_content] Warning: Source datablock with UUID {source_uuid} not found.")
            return {}

        results = {}
        outputs_for_type = _output_map.get(self.datablock_type, {})
        
        if self.datablock_type == 'SCENE':
            if source_datablock.collection:
                results[self.outputs['Master Collection'].identifier] = uuid_manager.get_or_create_uuid(source_datablock.collection)
            if source_datablock.world:
                results[self.outputs['World'].identifier] = uuid_manager.get_or_create_uuid(source_datablock.world)
            if source_datablock.camera:
                results[self.outputs['Active Camera'].identifier] = uuid_manager.get_or_create_uuid(source_datablock.camera)
        
        elif self.datablock_type == 'COLLECTION':
            results[self.outputs['Objects'].identifier] = [uuid_manager.get_or_create_uuid(obj) for obj in source_datablock.objects if obj]
            results[self.outputs['Child Collections'].identifier] = [uuid_manager.get_or_create_uuid(col) for col in source_datablock.children if col]

        elif self.datablock_type == 'OBJECT':
            # Note: Object Data can be of many types, we simplify to Mesh for now.
            # A more robust implementation would check `source_datablock.type`.
            if source_datablock.type == 'MESH' and source_datablock.data:
                 results[self.outputs['Object Data'].identifier] = uuid_manager.get_or_create_uuid(source_datablock.data)
            else:
                 results[self.outputs['Object Data'].identifier] = None
            
            if source_datablock.data and hasattr(source_datablock.data, 'materials'):
                results[self.outputs['Materials'].identifier] = [uuid_manager.get_or_create_uuid(mat) for mat in source_datablock.data.materials if mat]
            else:
                results[self.outputs['Materials'].identifier] = []

            if source_datablock.parent:
                results[self.outputs['Parent'].identifier] = uuid_manager.get_or_create_uuid(source_datablock.parent)
            else:
                results[self.outputs['Parent'].identifier] = None

            results[self.outputs['Children'].identifier] = [uuid_manager.get_or_create_uuid(child) for child in source_datablock.children if child]

        return results
