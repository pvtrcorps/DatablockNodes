import bpy
from .base import FNBaseNode
from .. import uuid_manager
from .. import logger
from .constants import DATABLOCK_TYPES, DATABLOCK_SOCKET_MAP

# This maps the EnumProperty items to bpy.data collections and socket types
_datablock_map = {
    'OBJECT': ('objects', DATABLOCK_SOCKET_MAP['OBJECT']),
    'SCENE': ('scenes', DATABLOCK_SOCKET_MAP['SCENE']),
    'COLLECTION': ('collections', DATABLOCK_SOCKET_MAP['COLLECTION']),
    'MATERIAL': ('materials', DATABLOCK_SOCKET_MAP['MATERIAL']),
    'MESH': ('meshes', DATABLOCK_SOCKET_MAP['MESH']),
    'LIGHT': ('lights', DATABLOCK_SOCKET_MAP['LIGHT']),
    'CAMERA': ('cameras', DATABLOCK_SOCKET_MAP['CAMERA']),
    'IMAGE': ('images', DATABLOCK_SOCKET_MAP['IMAGE']),
    'NODETREE': ('node_groups', DATABLOCK_SOCKET_MAP['NODETREE']),
    'TEXT': ('texts', DATABLOCK_SOCKET_MAP['TEXT']),
    'WORLD': ('worlds', DATABLOCK_SOCKET_MAP['WORLD']),
    'WORKSPACE': ('workspaces', DATABLOCK_SOCKET_MAP['WORKSPACE']),
}

def _update_node(self, context):
    self.update_sockets(context)

class FN_import_datablock(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_import_datablock"
    bl_label = "Import Datablock"

    datablock_type: bpy.props.EnumProperty(
        name="Type",
        items=DATABLOCK_TYPES,
        default='OBJECT',
        update=_update_node
    )

    # Using a StringProperty to store the name, as PointerProperty can be tricky
    # with dynamic types. We will use this for the name of the datablock to import.
    datablock_name: bpy.props.StringProperty(
        name="Name",
        description="Name of the datablock to import"
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear existing output sockets
        while len(self.outputs) > 0:
            self.outputs.remove(self.outputs[0])

        # Add the correct output socket based on the selected type
        _, socket_type = _datablock_map.get(self.datablock_type, (None, None))
        if socket_type:
            self.outputs.new(socket_type, "Datablock")

    

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type", text="Type")
        layout.prop(self, "datablock_name", text="Name")

    def execute(self, **kwargs):
        collection_name, _ = _datablock_map.get(self.datablock_type)
        
        if not collection_name or not self.datablock_name:
            logger.log(f"[FN_import_datablock] Error: Missing datablock type or name.")
            return None

        # Find the datablock in bpy.data
        datablock = getattr(bpy.data, collection_name).get(self.datablock_name)

        if not datablock:
            logger.log(f"[FN_import_datablock] Error: Datablock '{self.datablock_name}' of type '{self.datablock_type}' not found.")
            return None

        # Ensure the datablock has a UUID. If not, assign one.
        # This is a read-only operation for the node, the reconciler will persist it.
        datablock_uuid = uuid_manager.get_or_create_uuid(datablock)

        output_socket_identifier = self.outputs[0].identifier
        state_id = f"{self.fn_node_id}:{output_socket_identifier}"

        # Declare the desired state to the reconciler
        return {
            output_socket_identifier: datablock_uuid,
            'states': {
                state_id: datablock_uuid
            }
        }
