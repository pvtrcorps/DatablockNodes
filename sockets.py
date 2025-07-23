import bpy
from .proxy_types import DatablockProxy

# --- Helpers ---
def _color(r,g,b): return (r,g,b,1.0)

def _draw_value_socket(sock, layout, text, icon='NONE'):
    # In V5, the socket that carries the scene graph is FNSocketScene
    is_scene_socket = sock.bl_idname in ('FNSocketScene', 'FNSocketSceneList')

    if sock.is_output:
        row = layout.row(align=True)
        row.label(text=text or sock.name)
        if icon != 'NONE':
            row.label(text="", icon=icon)
        # The activation button is only shown on the main scene socket
        if is_scene_socket:
            icon_to_use = 'RADIOBUT_OFF'
            if sock.is_final_active:
                icon_to_use = 'RECORD_ON'
            elif sock.is_active:
                icon_to_use = 'RADIOBUT_ON'
            op = row.operator("fn.activate_socket", text="", icon=icon_to_use, emboss=False)
            op.node_id = sock.node.fn_node_id
            op.socket_identifier = sock.identifier
    elif sock.is_linked:
        layout.label(text=text or sock.name, icon=icon)
    else:
        # Standard property drawing for unconnected input sockets
        if hasattr(sock, 'default_value'):
            layout.prop(sock, 'default_value', text=text or sock.name, icon=icon)
        elif type(sock).bl_rna.properties.get('value') and isinstance(type(sock).bl_rna.properties['value'], bpy.types.PointerProperty):
             layout.prop(sock, 'value', text=text or sock.name, icon=icon)
        else:
            layout.label(text=text or sock.name, icon=icon)

# --- Base Class ---
class FN_SocketBase(bpy.types.NodeSocket):
    # The 'value' property is removed for now. In V5, sockets don't store complex
    # data directly. They are primarily connection points. The evaluation engine
    # passes DatablockProxy objects in memory.
    
    is_mutable: bpy.props.BoolProperty(default=False)
    is_active: bpy.props.BoolProperty(default=False)
    is_final_active: bpy.props.BoolProperty(default=False)

    def draw(self, context, layout, node, text):
        _draw_value_socket(self, layout, text, self.bl_icon if hasattr(self, 'bl_icon') else 'NONE')
        
    def draw_color(self, context, node):
        # Default color, can be overridden by specific socket types
        return (0.8, 0.8, 0.8, 1.0)

# --- Value Sockets (Unchanged) ---
class FNSocketString(FN_SocketBase): bl_idname='FNSocketString'; bl_label="String"; default_value:bpy.props.StringProperty(); draw_color=lambda s,c,n: _color(0.31,0.66,1.0)
class FNSocketInt(FN_SocketBase): bl_idname='FNSocketInt'; bl_label="Integer"; default_value:bpy.props.IntProperty(); draw_color=lambda s,c,n: _color(0.17,0.63,0.40)
class FNSocketFloat(FN_SocketBase): bl_idname='FNSocketFloat'; bl_label="Float"; default_value:bpy.props.FloatProperty(); draw_color=lambda s,c,n: _color(0.77,0.77,0.77)
class FNSocketBool(FN_SocketBase): bl_idname='FNSocketBool'; bl_label="Boolean"; default_value:bpy.props.BoolProperty(); draw_color=lambda s,c,n: _color(1.0,0.41,0.86)
class FNSocketVector(FN_SocketBase): bl_idname='FNSocketVector'; bl_label="Vector"; default_value:bpy.props.FloatVectorProperty(size=3); draw_color=lambda s,c,n: _color(0.38,0.38,0.78)
class FNSocketColor(FN_SocketBase): bl_idname='FNSocketColor'; bl_label="Color"; default_value:bpy.props.FloatVectorProperty(size=4,subtype='COLOR'); draw_color=lambda s,c,n: _color(0.8,0.8,0.2)
class FNSocketPulse(FN_SocketBase): bl_idname = "FNSocketPulse"; bl_label = "Pulse"; default_value: bpy.props.BoolProperty(default=False); draw_color=lambda s,c,n: (0.0, 0.0, 0.0, 1.0)

# --- V6 Core Sockets ---
class FNSocketScene(FN_SocketBase): 
    bl_idname="FNSocketScene"
    bl_label="Scene"
    
    def draw_color(self, context, node):
        return _color(0.9, 0.9, 0.9)

class FNSocketSceneList(FN_SocketBase): 
    bl_idname="FNSocketSceneList"
    bl_label="Scene List"
    
    def draw_color(self, context, node):
        return _color(0.9, 0.9, 0.9)

class FNSocketSelection(FN_SocketBase):
    bl_idname="FNSocketSelection"
    bl_label="Selection"

    def draw_color(self, context, node):
        return _color(0.2, 0.2, 0.2)

# --- Legacy Pointer & List Sockets (To be phased out, kept for now to avoid breaking old files) ---
class FNSocketObject(FN_SocketBase): bl_idname='FNSocketObject'; bl_label="Object"; value:bpy.props.PointerProperty(type=bpy.types.Object); draw_color=lambda s,c,n: _color(0.96,0.55,0.08)
class FNSocketCollection(FN_SocketBase): bl_idname='FNSocketCollection'; bl_label="Collection"; value:bpy.props.PointerProperty(type=bpy.types.Collection); draw_color=lambda s,c,n: _color(0.8,0.8,0.8)
# Note: The old FNSocketScene is now a legacy pointer socket. The new one is FNSocketScene.
class FNSocketScenePointer(FN_SocketBase): bl_idname='FNSocketScenePointer'; bl_label="Scene Pointer"; value:bpy.props.PointerProperty(type=bpy.types.Scene); draw_color=lambda s,c,n: _color(1.0,1.0,1.0)
class FNSocketMaterial(FN_SocketBase): bl_idname='FNSocketMaterial'; bl_label="Material"; value:bpy.props.PointerProperty(type=bpy.types.Material); draw_color=lambda s,c,n: _color(0.88,0.31,0.31)
class FNSocketObjectList(FN_SocketBase): bl_idname="FNSocketObjectList"; bl_label="Object List"; draw_color=lambda s,c,n: _color(0.96,0.55,0.08)
class FNSocketCollectionList(FN_SocketBase): bl_idname="FNSocketCollectionList"; bl_label="Collection List"; draw_color=lambda s,c,n: _color(0.8,0.8,0.8)


# --- Registration ---
_all_sockets = (
    # V6 Sockets
    FNSocketScene,
    FNSocketSceneList,
    FNSocketSelection,
    
    # Value Sockets
    FNSocketString, FNSocketInt, FNSocketFloat, FNSocketBool, FNSocketVector, FNSocketColor,
    FNSocketPulse,
    
    # Legacy Sockets (for file compatibility)
    FNSocketObject, FNSocketCollection, FNSocketScenePointer, FNSocketMaterial,
    FNSocketObjectList, FNSocketCollectionList,
)

def register():
    for cls in _all_sockets:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(_all_sockets):
        bpy.utils.unregister_class(cls)