import bpy

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

def register():
    bpy.utils.register_class(FNPropertyItem)

def unregister():
    bpy.utils.unregister_class(FNPropertyItem)