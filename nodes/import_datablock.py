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
        update=lambda self, context: self.update_sockets(context)
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
        tree = kwargs.get('tree')
        collection_name, _ = _datablock_map.get(self.datablock_type)
        
        if not collection_name or not self.datablock_name:
            print(f"[FN_import_datablock] Error: Missing datablock type or name.")
            return None

        # Find the datablock in bpy.data
        datablock = getattr(bpy.data, collection_name).get(self.datablock_name)

        if not datablock:
            print(f"[FN_import_datablock] Error: Datablock '{self.datablock_name}' of type '{self.datablock_type}' not found.")
            return None

        # Find the map item for this node and output socket
        output_socket_identifier = self.outputs[0].identifier
        map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id and item.socket_identifier == output_socket_identifier), None)

        # Check if the datablock is already managed by this node
        is_managed_by_this_node = False
        if map_item and map_item.datablock_uuids:
            managed_uuids = map_item.datablock_uuids.split(',')
            if uuid_manager.get_uuid(datablock) in managed_uuids:
                is_managed_by_this_node = True

        # Promote to managed if it's a manual datablock or not managed by this node yet
        if not uuid_manager.get_uuid(datablock) or not is_managed_by_this_node:
            print(f"[FN_import_datablock] Promoting '{datablock.name}' to a managed datablock.")
            uuid_manager.set_uuid(datablock) # Assign a new UUID if it doesn't have one
            
            # Update the state map
            if not map_item:
                map_item = tree.fn_state_map.add()
                map_item.node_id = self.fn_node_id
                map_item.datablock_uuids = uuid_manager.get_uuid(datablock)
            else:
                # Add the new UUID to the existing list if it's not already there
                current_uuids = map_item.datablock_uuids.split(',') if map_item.datablock_uuids else []
                if uuid_manager.get_uuid(datablock) not in current_uuids:
                    current_uuids.append(uuid_manager.get_uuid(datablock))
                map_item.datablock_uuids = ",".join(current_uuids)
        
        output_socket_identifier = self.outputs[0].identifier

        # Update the state map with socket_identifier
        if not map_item:
            map_item = tree.fn_state_map.add()
            map_item.node_id = self.fn_node_id
            map_item.socket_identifier = output_socket_identifier
            map_item.datablock_uuids = uuid_manager.get_uuid(datablock)
        else:
            # Find the specific map item for this node and socket
            found_socket_map_item = next((item for item in tree.fn_state_map if item.node_id == self.fn_node_id and item.socket_identifier == output_socket_identifier), None)
            if not found_socket_map_item:
                found_socket_map_item = tree.fn_state_map.add()
                found_socket_map_item.node_id = self.fn_node_id
                found_socket_map_item.socket_identifier = output_socket_identifier
            
            current_uuids = found_socket_map_item.datablock_uuids.split(',') if found_socket_map_item.datablock_uuids else []
            if uuid_manager.get_uuid(datablock) not in current_uuids:
                current_uuids.append(uuid_manager.get_uuid(datablock))
            found_socket_map_item.datablock_uuids = ",".join(current_uuids)

        return {output_socket_identifier: datablock}