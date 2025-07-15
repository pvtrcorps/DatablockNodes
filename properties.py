import bpy

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
    'OBJECT': lambda name: bpy.data.objects.new(name=name, object_data=None),
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

class FNPropertyItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property Name")

    def _update_rna_path(self, context):
        """Trigger socket updates on the owning node when the path changes."""
        try:
            id_data = self.id_data
            node_path = self.path_from_id().split(".")[0]
            node = id_data.path_resolve(node_path)
            if hasattr(node, "update_sockets"):
                node.update_sockets(context)
        except Exception:
            # Silently ignore if the path cannot be resolved
            pass

    rna_path: bpy.props.StringProperty(
        name="RNA Path",
        update=_update_rna_path,
    )
    socket_type: bpy.props.StringProperty(name="Socket Type")

class FNRnaPropertyItem(bpy.types.PropertyGroup):
    """Helper PropertyGroup to store a filtered, available RNA property for the search."""
    # The 'name' property is used by prop_search for display in the UI.
    # We will format it as: "UI Category > UI SubCategory > Property Name"
    name: bpy.props.StringProperty()
    # We store the actual rna_path separately to be used by the node.
    rna_path: bpy.props.StringProperty()
    # Store the description for tooltips.
    description: bpy.props.StringProperty()

class FNOverrideItem(bpy.types.PropertyGroup):
    datablock_uuid: bpy.props.StringProperty()
    datablock_type: bpy.props.StringProperty()
    override_data_json: bpy.props.StringProperty()

def register():
    bpy.utils.register_class(FNPropertyItem)
    bpy.utils.register_class(FNRnaPropertyItem)
    bpy.utils.register_class(FNOverrideItem)

def unregister():
    bpy.utils.unregister_class(FNPropertyItem)
    bpy.utils.unregister_class(FNRnaPropertyItem)
    bpy.utils.unregister_class(FNOverrideItem)