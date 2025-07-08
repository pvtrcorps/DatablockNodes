import bpy

### Helpers ###
def _color(r,g,b): return (r,g,b,1.0)

# Draw helper for value sockets. When the socket is not linked and is an input,
# expose its 'value' property so users can pick a value directly from the node.
def _draw_value_socket(sock, layout, text, icon='NONE'):
    show = getattr(sock, 'show_selector', True)
    
    if sock.is_output:
        # For output sockets, always draw text, then icon, then activate button
        row = layout.row(align=True)
        row.label(text=text or sock.name)
        # Always draw the icon if provided, regardless of whether it's a value socket or not.
        # List sockets set their icon in their own draw method, so we need to ensure it's drawn here.
        if icon != 'NONE':
            row.label(text="", icon=icon)
        
        # Only show activate button if the socket manages a scene datablock
        if sock.node.manages_scene_datablock:
            op = row.operator("fn.activate_socket", text="", icon='RADIOBUT_ON' if sock.is_active else 'RADIOBUT_OFF', emboss=False)
            op.node_id = sock.node.fn_node_id
            op.socket_identifier = sock.identifier

    elif sock.is_linked or not show:
        # For linked input sockets or hidden selectors, draw icon then text
        layout.label(text=text or sock.name, icon=icon)
    else:
        # For unlinked input sockets with selector, draw icon then property
        if hasattr(sock, 'default_value'):
            layout.prop(sock, 'default_value', text=text or sock.name, icon=icon)
        elif hasattr(sock, 'value'): # For PointerProperties like Object, Scene, etc.
            layout.prop(sock, 'value', text=text or sock.name, icon=icon)
        else:
            layout.label(text=text or sock.name, icon=icon)

# Base class for custom sockets
class FN_SocketBase(bpy.types.NodeSocket):
    # This property will be used by the reconciler to decide if a copy is needed.
    is_mutable: bpy.props.BoolProperty(
        name="Is Mutable",
        description="Determines if the node modifies the datablock passed to this socket.",
        default=False
    )
    show_selector: bpy.props.BoolProperty(default=True)
    is_active: bpy.props.BoolProperty(
        name="Is Active",
        description="If true, this socket's output is synchronized with the scene.",
        default=False
    )

    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, self.bl_icon if hasattr(self, 'bl_icon') else 'NONE')

    def draw_color(self, context, node):
        return (0.8, 0.8, 0.8, 1.0) # Default color

# Custom String Socket
class FNSocketString(FN_SocketBase):
    bl_idname = 'FNSocketString'
    bl_label = "String Socket"
    show_selector: bpy.props.BoolProperty(default=True)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text)
    def draw_color(self, context, node):
        return _color(0.3137, 0.6667, 1.0)
    default_value: bpy.props.StringProperty()

# Custom Object Socket
class FNSocketObject(FN_SocketBase):
    bl_idname = 'FNSocketObject'
    bl_label = "Object Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'OBJECT_DATA')
    def draw_color(self, context, node):
        return _color(0.9608, 0.5529, 0.0824)
    value: bpy.props.PointerProperty(type=bpy.types.Object)

# Custom Scene Socket
class FNSocketScene(FN_SocketBase):
    bl_idname = "FNSocketScene"
    bl_label = "Scene Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'SCENE_DATA')
    def draw_color(self, context, node):
        return _color(1.0, 1.0, 1.0)
    value: bpy.props.PointerProperty(type=bpy.types.Scene)

# Custom Mesh Socket
class FNSocketMesh(FN_SocketBase):
    bl_idname = "FNSocketMesh"
    bl_label = "Mesh Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'MESH_DATA')
    def draw_color(self, context, node):
        return _color(0.2118, 0.7529, 0.4471)
    value: bpy.props.PointerProperty(type=bpy.types.Mesh)

# Custom Light Socket
class FNSocketLight(FN_SocketBase):
    bl_idname = "FNSocketLight"
    bl_label = "Light Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'LIGHT_DATA')
    def draw_color(self, context, node):
        return _color(1.0, 0.9, 0.3)
    value: bpy.props.PointerProperty(type=bpy.types.Light)

# Custom Camera Socket
class FNSocketCamera(FN_SocketBase):
    bl_idname = "FNSocketCamera"
    bl_label = "Camera Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'CAMERA_DATA')
    def draw_color(self, context, node):
        return _color(0.8, 0.6, 0.4)
    value: bpy.props.PointerProperty(type=bpy.types.Camera)

# Custom Collection Socket
class FNSocketCollection(FN_SocketBase):
    bl_idname = "FNSocketCollection"
    bl_label = "Collection Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'OUTLINER_COLLECTION')
    def draw_color(self, context, node):
        return _color(0.8, 0.8, 0.8)
    value: bpy.props.PointerProperty(type=bpy.types.Collection)

# Custom World Socket
class FNSocketWorld(FN_SocketBase):
    bl_idname = "FNSocketWorld"
    bl_label = "World Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'WORLD')
    def draw_color(self, context, node):
        return _color(0.8, 0.8, 0.3)
    value: bpy.props.PointerProperty(type=bpy.types.World)

# Custom Image Socket
class FNSocketImage(FN_SocketBase):
    bl_idname = "FNSocketImage"
    bl_label = "Image Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'IMAGE_DATA')
    def draw_color(self, context, node):
        return _color(0.6, 0.6, 0.6)
    value: bpy.props.PointerProperty(type=bpy.types.Image)

# Custom Material Socket
class FNSocketMaterial(FN_SocketBase):
    bl_idname = "FNSocketMaterial"
    bl_label = "Material Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'MATERIAL_DATA')
    def draw_color(self, context, node):
        return _color(0.8863, 0.3137, 0.3137)
    value: bpy.props.PointerProperty(type=bpy.types.Material)

# Custom NodeTree Socket
class FNSocketNodeTree(FN_SocketBase):
    bl_idname = "FNSocketNodeTree"
    bl_label = "Node Tree Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'NODETREE')
    def draw_color(self, context, node):
        return _color(0.7, 0.9, 0.7)
    value: bpy.props.PointerProperty(type=bpy.types.NodeTree)

# Custom Text Socket
class FNSocketText(FN_SocketBase):
    bl_idname = "FNSocketText"
    bl_label = "Text Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'TEXT')
    def draw_color(self, context, node):
        return _color(0.9, 0.9, 0.6)
    value: bpy.props.PointerProperty(type=bpy.types.Text)

# Custom WorkSpace Socket
class FNSocketWorkSpace(FN_SocketBase):
    bl_idname = "FNSocketWorkSpace"
    bl_label = "WorkSpace Socket"
    is_mutable: bpy.props.BoolProperty(default=True)
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'WORKSPACE')
    def draw_color(self, context, node):
        return _color(0.5, 0.7, 0.9)
    value: bpy.props.PointerProperty(type=bpy.types.WorkSpace)

# Custom Bool Socket
class FNSocketBool(FN_SocketBase):
    bl_idname = "FNSocketBool"
    bl_label = "Boolean Socket"
    show_selector: bpy.props.BoolProperty(default=True)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text)
    def draw_color(self, context, node):
        return _color(1.0, 0.4118, 0.8627)
    default_value: bpy.props.BoolProperty()

# Custom Float Socket
class FNSocketFloat(FN_SocketBase):
    bl_idname = "FNSocketFloat"
    bl_label = "Float Socket"
    show_selector: bpy.props.BoolProperty(default=True)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text)
    def draw_color(self, context, node):
        return _color(0.7765, 0.7765, 0.7765)
    default_value: bpy.props.FloatProperty()

# Custom Int Socket
class FNSocketInt(FN_SocketBase):
    bl_idname = "FNSocketInt"
    bl_label = "Integer Socket"
    show_selector: bpy.props.BoolProperty(default=True)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text)
    def draw_color(self, context, node):
        return _color(0.1765, 0.6392, 0.4078)
    default_value: bpy.props.IntProperty()

# Custom Vector Socket
class FNSocketVector(FN_SocketBase):
    bl_idname = "FNSocketVector"
    bl_label = "Vector Socket"
    show_selector: bpy.props.BoolProperty(default=True)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text)
    def draw_color(self, context, node):
        return _color(0.3882, 0.3882, 0.7804)
    default_value: bpy.props.FloatVectorProperty(size=3)

# Custom Color Socket
class FNSocketColor(FN_SocketBase):
    bl_idname = "FNSocketColor"
    bl_label = "Color Socket"
    show_selector: bpy.props.BoolProperty(default=True)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text)
    def draw_color(self, context, node):
        return _color(0.8, 0.8, 0.2)
    default_value: bpy.props.FloatVectorProperty(size=4, subtype='COLOR')

class FNSocketSceneList(FN_SocketBase):
    bl_idname = "FNSocketSceneList"
    bl_label = "Scene List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'SCENE_DATA')
    def draw_color(self, context, node):
        return _color(1.0, 1.0, 1.0)

class FNSocketObjectList(FN_SocketBase):
    bl_idname = "FNSocketObjectList"
    bl_label = "Object List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'OBJECT_DATA')
    def draw_color(self, context, node):
        return _color(0.9608, 0.5529, 0.0824)

class FNSocketCollectionList(FN_SocketBase):
    bl_idname = "FNSocketCollectionList"
    bl_label = "Collection List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'OUTLINER_COLLECTION')
    def draw_color(self, context, node):
        return _color(1.0, 1.0, 1.0)

class FNSocketWorldList(FN_SocketBase):
    bl_idname = "FNSocketWorldList"
    bl_label = "World List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'WORLD')
    def draw_color(self, context, node):
        return _color(0.8, 0.8, 0.3)

class FNSocketCameraList(FN_SocketBase):
    bl_idname = "FNSocketCameraList"
    bl_label = "Camera List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'CAMERA_DATA')
    def draw_color(self, context, node):
        return _color(0.8, 0.6, 0.4)

class FNSocketImageList(FN_SocketBase):
    bl_idname = "FNSocketImageList"
    bl_label = "Image List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'IMAGE_DATA')
    def draw_color(self, context, node):
        return _color(0.6, 0.6, 0.6)

class FNSocketLightList(FN_SocketBase):
    bl_idname = "FNSocketLightList"
    bl_label = "Light List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'LIGHT_DATA')
    def draw_color(self, context, node):
        return _color(1.0, 0.9, 0.3)

class FNSocketMaterialList(FN_SocketBase):
    bl_idname = "FNSocketMaterialList"
    bl_label = "Material List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'MATERIAL_DATA')
    def draw_color(self, context, node):
        return _color(0.8863, 0.3137, 0.3137)

class FNSocketMeshList(FN_SocketBase):
    bl_idname = "FNSocketMeshList"
    bl_label = "Mesh List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'MESH_DATA')
    def draw_color(self, context, node):
        return _color(0.2118, 0.7529, 0.4471)

class FNSocketNodeTreeList(FN_SocketBase):
    bl_idname = "FNSocketNodeTreeList"
    bl_label = "Node Tree List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'NODETREE')
    def draw_color(self, context, node):
        return _color(0.7, 0.9, 0.7)

class FNSocketTextList(FN_SocketBase):
    bl_idname = "FNSocketTextList"
    bl_label = "Text List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'TEXT')
    def draw_color(self, context, node):
        return _color(0.9, 0.9, 0.6)

class FNSocketWorkSpaceList(FN_SocketBase):
    bl_idname = "FNSocketWorkSpaceList"
    bl_label = "WorkSpace List"
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'WORKSPACE')
    def draw_color(self, context, node):
        return _color(0.5, 0.7, 0.9)

class FNSocketStringList(FN_SocketBase):
    bl_idname = "FNSocketStringList"
    bl_label = "String List"
    is_mutable: bpy.props.BoolProperty(default=True)
    display_shape = 'SQUARE'
    show_selector: bpy.props.BoolProperty(default=False)
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'NONE')
    def draw_color(self, context, node):
        return _color(0.3137, 0.6667, 1.0)

class FNSocketViewLayerList(FN_SocketBase):
    bl_idname = "FNSocketViewLayerList"
    bl_label = "View Layer List"
    is_mutable: bpy.props.BoolProperty(default=True)
    display_shape = 'SQUARE'
    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, 'RENDERLAYERS')
    def draw_color(self, context, node):
        return _color(0.6, 0.6, 0.6)
    # Blender does not support PointerProperty for ViewLayer, store the name instead.
    value: bpy.props.StringProperty()



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