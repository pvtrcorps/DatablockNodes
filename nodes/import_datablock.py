import bpy
from .base import FNBaseNode
from .. import uuid_manager

# This maps the EnumProperty items to bpy.data collections and socket types
_datablock_map = {
    'OBJECT': ('objects', 'FNSocketObject'),
    'SCENE': ('scenes', 'FNSocketScene'),
    'COLLECTION': ('collections', 'FNSocketCollection'),
    'MATERIAL': ('materials', 'FNSocketMaterial'),
    'MESH': ('meshes', 'FNSocketMesh'),
    'LIGHT': ('lights', 'FNSocketLight'),
    'CAMERA': ('cameras', 'FNSocketCamera'),
    'IMAGE': ('images', 'FNSocketImage'),
    'NODETREE': ('node_groups', 'FNSocketNodeTree'),
    'TEXT': ('texts', 'FNSocketText'),
    'WORLD': ('worlds', 'FNSocketWorld'),
    'WORKSPACE': ('workspaces', 'FNSocketWorkSpace'),
}

def _update_node(self, context):
    self.update_sockets(context)

class FN_import_datablock(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_import_datablock"
    bl_label = "Import Datablock"

    datablock_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ('OBJECT', 'Object', ''),
            ('SCENE', 'Scene', ''),
            ('COLLECTION', 'Collection', ''),
            ('MATERIAL', 'Material', ''),
            ('MESH', 'Mesh', ''),
            ('LIGHT', 'Light', ''),
            ('CAMERA', 'Camera', ''),
            ('IMAGE', 'Image', ''),
            ('NODETREE', 'Node Tree', ''),
            ('TEXT', 'Text', ''),
            ('WORLD', 'World', ''),
            ('WORKSPACE', 'WorkSpace', ''),
        ],
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
            print(f"[FN_import_datablock] Error: Missing datablock type or name.")
            return None

        # Find the datablock in bpy.data
        datablock = getattr(bpy.data, collection_name).get(self.datablock_name)

        if not datablock:
            print(f"[FN_import_datablock] Error: Datablock '{self.datablock_name}' of type '{self.datablock_type}' not found.")
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
