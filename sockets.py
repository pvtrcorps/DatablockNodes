import bpy

# Base class for custom sockets
class FN_SocketBase(bpy.types.NodeSocket):
    # This property will be used by the reconciler to decide if a copy is needed.
    is_mutable: bpy.props.BoolProperty(
        name="Is Mutable",
        description="Determines if the node modifies the datablock passed to this socket.",
        default=False
    )

    def draw(self, context, layout, node, text):
        if self.is_linked or self.is_output:
            layout.label(text=text)
        else:
            if hasattr(self, "default_value"):
                layout.prop(self, "default_value", text=text)
            else:
                layout.label(text=text) # Fallback for sockets without default_value (like lists)

    def draw_color(self, context, node):
        return (0.8, 0.8, 0.8, 1.0) # Default color

# Custom String Socket
class FNSocketString(FN_SocketBase):
    bl_idname = 'FNSocketString'
    bl_label = "String Socket"
    default_value: bpy.props.StringProperty()

    def draw_color(self, context, node):
        return (0.3, 0.6, 0.9, 1.0) # Blue

# Custom Object Socket
class FNSocketObject(FN_SocketBase):
    bl_idname = 'FNSocketObject'
    bl_label = "Object Socket"
    is_mutable: bpy.props.BoolProperty(default=True)

    def draw_color(self, context, node):
        return (0.9, 0.6, 0.3, 1.0) # Orange

# Custom Scene Socket
class FNSocketScene(FN_SocketBase):
    bl_idname = 'FNSocketScene'
    bl_label = "Scene Socket"

    def draw_color(self, context, node):
        return (1.0, 1.0, 1.0, 1.0) # White

# Custom Mesh Socket
class FNSocketMesh(FN_SocketBase):
    bl_idname = 'FNSocketMesh'
    bl_label = "Mesh Socket"

    def draw_color(self, context, node):
        return (0.3, 0.9, 0.6, 1.0) # Cyan

# Custom Light Socket
class FNSocketLight(FN_SocketBase):
    bl_idname = 'FNSocketLight'
    bl_label = "Light Socket"

    def draw_color(self, context, node):
        return (0.9, 0.9, 0.3, 1.0) # Yellow

# Custom Camera Socket
class FNSocketCamera(FN_SocketBase):
    bl_idname = 'FNSocketCamera'
    bl_label = "Camera Socket"

    def draw_color(self, context, node):
        return (0.9, 0.3, 0.9, 1.0) # Magenta

# Custom Collection Socket
class FNSocketCollection(FN_SocketBase):
    bl_idname = 'FNSocketCollection'
    bl_label = "Collection Socket"

    def draw_color(self, context, node):
        return (0.8, 0.8, 0.8, 1.0) # Light Gray

# Custom World Socket
class FNSocketWorld(FN_SocketBase):
    bl_idname = 'FNSocketWorld'
    bl_label = "World Socket"

    def draw_color(self, context, node):
        return (0.9, 0.3, 0.9, 1.0) # Magenta

# Custom Image Socket
class FNSocketImage(FN_SocketBase):
    bl_idname = 'FNSocketImage'
    bl_label = "Image Socket"

    def draw_color(self, context, node):
        return (0.6, 0.9, 0.3, 1.0) # Green

# Custom Material Socket
class FNSocketMaterial(FN_SocketBase):
    bl_idname = 'FNSocketMaterial'
    bl_label = "Material Socket"

    def draw_color(self, context, node):
        return (0.9, 0.6, 0.3, 1.0) # Orange

# Custom NodeTree Socket
class FNSocketNodeTree(FN_SocketBase):
    bl_idname = 'FNSocketNodeTree'
    bl_label = "Node Tree Socket"

    def draw_color(self, context, node):
        return (0.3, 0.9, 0.6, 1.0) # Cyan

# Custom Text Socket
class FNSocketText(FN_SocketBase):
    bl_idname = 'FNSocketText'
    bl_label = "Text Socket"

    def draw_color(self, context, node):
        return (0.9, 0.9, 0.3, 1.0) # Yellow

# Custom WorkSpace Socket
class FNSocketWorkSpace(FN_SocketBase):
    bl_idname = 'FNSocketWorkSpace'
    bl_label = "WorkSpace Socket"

    def draw_color(self, context, node):
        return (0.3, 0.3, 0.9, 1.0) # Dark Blue

# Custom Bool Socket
class FNSocketBool(FN_SocketBase):
    bl_idname = 'FNSocketBool'
    bl_label = "Boolean Socket"
    default_value: bpy.props.BoolProperty()

    def draw_color(self, context, node):
        return (0.9, 0.3, 0.3, 1.0) # Red

# Custom Float Socket
class FNSocketFloat(FN_SocketBase):
    bl_idname = 'FNSocketFloat'
    bl_label = "Float Socket"
    default_value: bpy.props.FloatProperty()

    def draw_color(self, context, node):
        return (0.3, 0.9, 0.9, 1.0) # Cyan

# Custom Int Socket
class FNSocketInt(FN_SocketBase):
    bl_idname = 'FNSocketInt'
    bl_label = "Integer Socket"
    default_value: bpy.props.IntProperty()

    def draw_color(self, context, node):
        return (0.9, 0.3, 0.9, 1.0) # Magenta

# Custom Vector Socket
class FNSocketVector(FN_SocketBase):
    bl_idname = 'FNSocketVector'
    bl_label = "Vector Socket"
    default_value: bpy.props.FloatVectorProperty(size=3)

    def draw_color(self, context, node):
        return (0.3, 0.3, 0.9, 1.0) # Dark Blue

# Custom Color Socket
class FNSocketColor(FN_SocketBase):
    bl_idname = 'FNSocketColor'
    bl_label = "Color Socket"
    default_value: bpy.props.FloatVectorProperty(size=4, subtype='COLOR')

    def draw_color(self, context, node):
        return (0.9, 0.9, 0.3, 1.0) # Yellow

class FNSocketSceneList(FN_SocketBase):
    bl_idname = "FNSocketSceneList"
    bl_label = "Scene List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (1.0, 1.0, 1.0, 1.0) # White

class FNSocketObjectList(FN_SocketBase):
    bl_idname = "FNSocketObjectList"
    bl_label = "Object List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.9, 0.6, 0.3, 1.0)

class FNSocketCollectionList(FN_SocketBase):
    bl_idname = "FNSocketCollectionList"
    bl_label = "Collection List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.8, 0.8, 0.8, 1.0) # Light Gray

class FNSocketWorldList(FN_SocketBase):
    bl_idname = "FNSocketWorldList"
    bl_label = "World List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.9, 0.3, 0.9, 1.0)

class FNSocketCameraList(FN_SocketBase):
    bl_idname = "FNSocketCameraList"
    bl_label = "Camera List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.9, 0.3, 0.9, 1.0)

class FNSocketImageList(FN_SocketBase):
    bl_idname = "FNSocketImageList"
    bl_label = "Image List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.6, 0.9, 0.3, 1.0)

class FNSocketLightList(FN_SocketBase):
    bl_idname = "FNSocketLightList"
    bl_label = "Light List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.9, 0.9, 0.3, 1.0)

class FNSocketMaterialList(FN_SocketBase):
    bl_idname = "FNSocketMaterialList"
    bl_label = "Material List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.9, 0.6, 0.3, 1.0)

class FNSocketMeshList(FN_SocketBase):
    bl_idname = "FNSocketMeshList"
    bl_label = "Mesh List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.3, 0.9, 0.6, 1.0)

class FNSocketNodeTreeList(FN_SocketBase):
    bl_idname = "FNSocketNodeTreeList"
    bl_label = "Node Tree List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.3, 0.9, 0.6, 1.0)

class FNSocketTextList(FN_SocketBase):
    bl_idname = "FNSocketTextList"
    bl_label = "Text List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.9, 0.9, 0.3, 1.0)

class FNSocketWorkSpaceList(FN_SocketBase):
    bl_idname = "FNSocketWorkSpaceList"
    bl_label = "WorkSpace List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.3, 0.3, 0.9, 1.0)

class FNSocketStringList(FN_SocketBase):
    bl_idname = "FNSocketStringList"
    bl_label = "String List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.3, 0.6, 0.9, 1.0) # Blue, same as FNSocketString

class FNSocketViewLayerList(FN_SocketBase):
    bl_idname = "FNSocketViewLayerList"
    bl_label = "View Layer List"
    display_shape = 'SQUARE'
    def draw_color(self, context, node):
        return (0.6, 0.6, 0.6, 1.0)

_all_sockets = (
    FNSocketString,
    FNSocketBool,
    FNSocketFloat,
    FNSocketInt,
    FNSocketVector,
    FNSocketColor,
    FNSocketObject,
    FNSocketScene,
    FNSocketMesh,
    FNSocketLight,
    FNSocketCamera,
    FNSocketCollection,
    FNSocketWorld,
    FNSocketImage,
    FNSocketMaterial,
    FNSocketNodeTree,
    FNSocketText,
    FNSocketWorkSpace,
    FNSocketSceneList,
    FNSocketObjectList,
    FNSocketCollectionList,
    FNSocketWorldList,
    FNSocketCameraList,
    FNSocketImageList,
    FNSocketLightList,
    FNSocketMaterialList,
    FNSocketMeshList,
    FNSocketNodeTreeList,
    FNSocketTextList,
    FNSocketWorkSpaceList,
    FNSocketViewLayerList,
    FNSocketStringList,
)

def register():
    for cls in _all_sockets:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(_all_sockets):
        bpy.utils.unregister_class(cls)