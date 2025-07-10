
import bpy
from ..nodes.base import FNBaseNode
from .. import properties # Import the new properties module
from .. import reconciler # Import reconciler for property setting
from ..sockets import (
    FNSocketBool, FNSocketFloat, FNSocketInt, FNSocketString, FNSocketVector, FNSocketColor,
    FNSocketScene, FNSocketObject, FNSocketCollection, FNSocketCamera,
    FNSocketImage, FNSocketLight, FNSocketMaterial, FNSocketMesh, FNSocketNodeTree,
    FNSocketText, FNSocketWorkSpace, FNSocketWorld
)

# Map Blender RNA types to our custom socket types
_rna_type_to_socket_map = {
    'BOOLEAN': 'FNSocketBool',
    'INT': 'FNSocketInt',
    'FLOAT': 'FNSocketFloat',
    'STRING': 'FNSocketString',
    'ENUM': 'FNSocketString', # Enums can be represented as strings
    'FLOAT_VECTOR': 'FNSocketVector',
    'COLOR': 'FNSocketColor',
    # Add more mappings as needed
}

# Map Blender datablock types to their corresponding socket types
_datablock_type_to_socket_map = {
    'OBJECT': 'FNSocketObject',
    'SCENE': 'FNSocketScene',
    'COLLECTION': 'FNSocketCollection',
    'MATERIAL': 'FNSocketMaterial',
    'MESH': 'FNSocketMesh',
    'LIGHT': 'FNSocketLight',
    'CAMERA': 'FNSocketCamera',
    'IMAGE': 'FNSocketImage',
    'NODETREE': 'FNSocketNodeTree',
    'TEXT': 'FNSocketText',
    'WORLD': 'FNSocketWorld',
    'WORKSPACE': 'FNSocketWorkSpace',
}

class FN_set_datablock_properties(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_datablock_properties"
    bl_label = "Set Datablock Properties"

    datablock_type: bpy.props.EnumProperty(
        name="Datablock Type",
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

    # Collection to store the properties the user wants to set
    properties_to_set: bpy.props.CollectionProperty(type=properties.FNPropertyItem)

    def init(self, context):
        FNBaseNode.init(self, context)
        self.update_sockets(context)

    def update_sockets(self, context):
        # Clear ALL existing inputs/outputs
        for socket in list(self.inputs):
            self.inputs.remove(socket)
        for socket in list(self.outputs):
            self.outputs.remove(socket)

        # Add main datablock input socket
        main_datablock_socket_type = _datablock_type_to_socket_map.get(self.datablock_type)
        if main_datablock_socket_type:
            main_input = self.inputs.new(main_datablock_socket_type, "Datablock")
            main_input.is_mutable = True # This node modifies the input datablock
            self.outputs.new(main_datablock_socket_type, "Datablock")

        # Update socket types for properties_to_set and then add dynamic input sockets
        rna_type = getattr(bpy.types, self.datablock_type.title(), None)
        if rna_type:
            for prop_item in self.properties_to_set:
                if prop_item.rna_path:
                    # Try to get the RNA property from the rna_path
                    rna_property = rna_type.bl_rna.properties.get(prop_item.rna_path)
                    if rna_property:
                        # Store the Blender RNA property type
                        prop_item.socket_type = rna_property.type
                    else:
                        prop_item.socket_type = 'STRING' # Default if rna_path is invalid
                else:
                    prop_item.socket_type = 'STRING' # Default if rna_path is not set yet

                # Use the determined socket_type (Blender RNA property type) to get the actual socket bl_idname
                socket_bl_idname = _rna_type_to_socket_map.get(prop_item.socket_type)
                if socket_bl_idname:
                    self.inputs.new(socket_bl_idname, prop_item.name)

    def update_hash(self, hasher):
        super().update_hash(hasher)
        hasher.update(self.datablock_type.encode())
        for prop_item in self.properties_to_set:
            hasher.update(prop_item.rna_path.encode())
            hasher.update(prop_item.socket_type.encode())

    def draw_buttons(self, context, layout):
        layout.prop(self, "datablock_type")

        # UI for adding/removing properties
        box = layout.box()
        box.label(text="Properties to Set:")
        for i, prop_item in enumerate(self.properties_to_set):
            row = box.row(align=True)
            # Use prop_search for selecting properties
            row.prop_search(prop_item, "rna_path", 
                            getattr(bpy.types, self.datablock_type.title()).bl_rna, "properties", 
                            text="")
            # Add a remove button
            remove_op = row.operator("fn.remove_property_from_set", text="", icon='X')
            remove_op.node_id = self.fn_node_id
            remove_op.property_index = i

        add_op = box.operator("fn.add_property_to_set", text="Add Property", icon='ADD')
        add_op.node_id = self.fn_node_id
        add_op.datablock_type = self.datablock_type

    def execute(self, **kwargs):
        input_datablock = kwargs.get(self.inputs["Datablock"].identifier)
        if not input_datablock:
            return None

        # Apply each property from the inputs to the datablock
        for prop_item in self.properties_to_set:
            prop_value = kwargs.get(self.inputs[prop_item.name].identifier)
            if prop_value is not None:
                reconciler._set_rna_property_value(input_datablock, prop_item.rna_path, prop_value)

        return {self.outputs[0].identifier: input_datablock}
