"""Funciones de utilidad para el motor de ejecución."""
import bpy
import mathutils
import json
import warnings
import fnmatch
from bpy.types import bpy_prop_array
from .. import uuid_manager
from ..proxy_types import DatablockProxy
from ..query_types import FNSelectionQuery

# Conjuntos para una comprobación de exclusión más rápida y limpia
PROPS_BLACKLIST = {
    'rna_type', 'name', 'users', 'id_data', 'layout', 'panel',
    'animation_data', 'is_runtime_data', 'use_extra_user',
    'matrix_world', 'matrix_local', 'matrix_basis'
}

PATH_PREFIX_BLACKLIST = {
    'tool_settings',
    'statistics',
    'grease_pencil_settings'
}

def to_json_safe(value):
    if isinstance(value, (int, float, str, bool, type(None))):
        return value
    if isinstance(value, (mathutils.Vector, mathutils.Color, mathutils.Euler, mathutils.Quaternion)):
        return list(value)
    if isinstance(value, mathutils.Matrix):
        return [list(row) for row in value]
    if isinstance(value, bpy_prop_array):
        return [to_json_safe(item) for item in value]
    if hasattr(value, 'bl_rna'): # Tratar todos los tipos de Blender que no son datablocks
        if isinstance(value, bpy.types.ID):
            managed_uuid = uuid_manager.get_uuid(value)
            if managed_uuid:
                return {'_type': 'UUID_POINTER', 'value': str(managed_uuid)}
            return {'_type': 'NAME_POINTER', 'value': getattr(value, 'name', '')}
    if isinstance(value, (list, tuple)):
        return [to_json_safe(item) for item in value]
    return None

def from_json_safe(value):
    if isinstance(value, dict):
        if value.get('_type') == 'UUID_POINTER':
            return uuid_manager.find_datablock_by_uuid(value['value'])
    if isinstance(value, list):
        return value
    return value

def set_nested_property(base, path, value):
    try:
        parts = path.split('.')
        obj = base
        for part in parts[:-1]:
            obj = getattr(obj, part)
        prop_name = parts[-1]
        prop = getattr(obj, prop_name)
        if isinstance(value, list):
            if isinstance(prop, mathutils.Vector): value = mathutils.Vector(value)
            elif isinstance(prop, mathutils.Color): value = mathutils.Color(value)
            elif isinstance(prop, mathutils.Euler): value = mathutils.Euler(value)
            elif isinstance(prop, mathutils.Quaternion): value = mathutils.Quaternion(value)
            elif isinstance(prop, mathutils.Matrix): value = mathutils.Matrix(value)
        setattr(obj, prop_name, value)
        return True
    except (AttributeError, TypeError, ValueError):
        return False

def capture_initial_state(datablock):
    """
    Captures the properties of a datablock into a JSON-serializable dictionary.
    This is used to create a "snapshot" of the state defined by the nodes.
    """
    state_dict = {}
    visited_rna_structs = set()

    def _recursive_capture(base_obj, path_prefix=""):
        struct_id = base_obj.bl_rna.identifier
        if (struct_id, path_prefix) in visited_rna_structs:
            return
        visited_rna_structs.add((struct_id, path_prefix))

        for prop in base_obj.bl_rna.properties:
            if prop.identifier in PROPS_BLACKLIST:
                continue

            prop_path = f"{path_prefix}{prop.identifier}"
            
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    current_value = getattr(base_obj, prop.identifier)
            except AttributeError:
                continue

            if prop.type == 'POINTER' and hasattr(current_value, 'bl_rna') and not isinstance(current_value, bpy.types.ID):
                if prop.identifier in PATH_PREFIX_BLACKLIST:
                    continue
                _recursive_capture(current_value, f"{prop_path}.")
                continue

            if not prop.is_readonly:
                safe_value = to_json_safe(current_value)
                if safe_value is not None:
                    state_dict[prop_path] = safe_value

    _recursive_capture(datablock)
    return state_dict

def resolve_selection(root_proxy: DatablockProxy, query: FNSelectionQuery) -> list[DatablockProxy]:
    """
    Finds and returns a list of prims in the scene graph that match the given query.
    """
    if not root_proxy or not query:
        return []

    all_prims = []
    nodes_to_visit = [root_proxy]
    while nodes_to_visit:
        node = nodes_to_visit.pop(0)
        all_prims.append(node)
        nodes_to_visit.extend(node.children)

    path_pattern = query.path_glob
    path_matched_prims = [p for p in all_prims if fnmatch.fnmatch(p.path, path_pattern)]

    if not query.filters:
        return path_matched_prims

    filtered_prims = []
    for prim in path_matched_prims:
        match_all_filters = True
        for f in query.filters:
            key = f.get('key')
            op = f.get('op')
            value = f.get('value')

            if key == 'type':
                prim_type = prim.properties.get('datablock_type')
                if not (op == 'eq' and prim_type == value):
                    match_all_filters = False
                    break
        
        if match_all_filters:
            filtered_prims.append(prim)

    return filtered_prims

def parse_multi_target_string(input_string: str) -> list[str]:
    """Parses a comma-separated string into a list of clean names."""
    if not input_string:
        return []
    return [name.strip() for name in input_string.split(',') if name.strip()]