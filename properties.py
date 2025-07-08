import bpy

class FNPropertyItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property Name")
    rna_path: bpy.props.StringProperty(name="RNA Path")
    socket_type: bpy.props.StringProperty(name="Socket Type")

def register():
    bpy.utils.register_class(FNPropertyItem)

def unregister():
    bpy.utils.unregister_class(FNPropertyItem)