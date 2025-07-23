"""Punto de Entrada: La conexión entre los Handlers de Blender y nuestro motor."""
import bpy
from . import orchestrator

# Este es el handler que se registrará en Blender.
# Su única responsabilidad es encontrar el árbol correcto y lanzar el motor.
@bpy.app.handlers.persistent
def depsgraph_update_handler(scene, depsgraph):
    # No buscar el árbol si no hay un editor de nodos visible con nuestro tipo de árbol.
    # Esto es una optimización de rendimiento crucial.
    active_tree = None
    for area in getattr(bpy.context, 'screen', {}).get('areas', []):
        if area.type == 'NODE_EDITOR':
            space = area.spaces.active
            if hasattr(space, 'tree_type') and space.tree_type == 'DatablockTreeType':
                active_tree = space.edit_tree
                break
    
    # Si no encontramos un árbol activo en un editor visible, no hacemos nada.
    if not active_tree:
        return

    # Lanzamos el motor con el árbol correcto.
    orchestrator.execute_node_tree(active_tree, depsgraph)