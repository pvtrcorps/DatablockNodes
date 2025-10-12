"""Funciones de utilidad para el motor de ejecución."""
import bpy
import mathutils
import json
import warnings

from bpy.types import bpy_prop_array
from .. import logger
from .. import uuid_manager
from ..proxy_types import DatablockProxy


# Conjuntos para una comprobación de exclusión más rápida y limpia
PROPS_BLACKLIST = {
    'rna_type', 'name', 'users', 'id_data', 'layout', 'panel',
    'animation_data', 'is_runtime_data', 'use_extra_user',
    'matrix_world', 'matrix_local', 'matrix_basis'
}

PATH_PREFIX_BLACKLIST = {
    'tool_settings',
    'statistics',
    'preview',
    'cursor',
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
            return {'_type': 'NAME_POINTER', 'value': getattr(value, 'name', ''), 'bl_type': value.bl_rna.identifier}
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
    #logger.log(f"[Utils] set_nested_property called: base={base.name if hasattr(base, 'name') else base}, path='{path}', value={value}")
    try:
        parts = path.split('.')
        obj = base
        for i, part in enumerate(parts[:-1]):
            #logger.log(f"[Utils] Traversing path: part='{part}', current_obj={obj.name if hasattr(obj, 'name') else obj}")
            # Handle both dict and object attribute access
            try:
                if isinstance(obj, dict):
                    obj = obj[part]
                else:
                    obj = getattr(obj, part)
            except (KeyError, AttributeError):
                #logger.log(f"[Utils] Path part '{part}' not found on {obj.name if hasattr(obj, 'name') else obj}. Cannot set property.")
                return False # Path does not exist, cannot set property
        prop_name = parts[-1]

        # --- Optimization: Only write the property if the value has changed ---
        # Handle both dict and object attribute access
        try:
            if isinstance(obj, dict):
                current_value = obj.get(prop_name)
            else:
                current_value = getattr(obj, prop_name)
        except AttributeError:
            #logger.log(f"[Utils] Property '{prop_name}' not found on {obj.name if hasattr(obj, 'name') else obj}. Cannot set property.")
            return False # Property does not exist, cannot set property
        #logger.log(f"[Utils] Current value of '{prop_name}': {current_value}")
        
        # Convert list to mathutils type for proper comparison
        if isinstance(value, list):
            if isinstance(current_value, mathutils.Vector): 
                value = mathutils.Vector(value)
            elif isinstance(current_value, mathutils.Color): 
                value = mathutils.Color(value)
            elif isinstance(current_value, mathutils.Euler): 
                value = mathutils.Euler(value)
            elif isinstance(current_value, mathutils.Quaternion): 
                value = mathutils.Quaternion(value)
            elif isinstance(current_value, mathutils.Matrix): 
                value = mathutils.Matrix(value)

        if current_value == value:
            #logger.log(f"[Utils] Value for '{prop_name}' is already the same. Skipping set.")
            return True # Value is the same, no need to set it. Success.

        # Handle both dict and object attribute access
        if isinstance(obj, dict):
            obj[prop_name] = value
        else:
            setattr(obj, prop_name, value)
        #logger.log(f"[Utils] Successfully set '{prop_name}' to '{value}'.")
        return True
    except (AttributeError, TypeError, ValueError, KeyError) as e: # Added KeyError
        #logger.log(f"[Utils] Error setting property '{path}' on {base.name if hasattr(base, 'name') else base}: {e}", level='ERROR')
        return False

from . import constants

def capture_datablock_state(datablock: bpy.types.ID) -> dict:
    """
    Captures the full, deep state of an existing Blender datablock.
    This is the canonical function for capturing state, used by the parser,
    the override system, and any other part of the addon that needs to
    understand a datablock's properties.
    """
    if not datablock:
        return {}
        
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
    
    # Add the fundamental properties that are not captured in the loop.
    state_dict['name'] = datablock.name
    
    # Normalize the datablock type to our internal canonical form
    blender_type = datablock.bl_rna.identifier
    canonical_type = constants.BLENDER_TO_FN_TYPE.get(blender_type, blender_type.upper())
    state_dict['datablock_type'] = canonical_type
    
    return state_dict



def parse_multi_target_string(input_string: str) -> list[str]:
    """Parses a comma-separated string into a list of clean names."""
    if not input_string:
        return []
    return [name.strip() for name in input_string.split(',') if name.strip()]