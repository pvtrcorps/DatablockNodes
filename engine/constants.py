"""
Central source of truth for all pathing, naming, and type conventions.
This module ensures that the entire addon speaks the same language.
"""

# --- Namespace Names ---
# Canonical names for the organizational proxies in the scene graph.
OBJECTS_NAMESPACE = "objects"
MESHES_NAMESPACE = "meshes"
LIGHTS_NAMESPACE = "lights"
MATERIALS_NAMESPACE = "materials"
CAMERAS_NAMESPACE = "cameras"
CURVES_NAMESPACE = "curves"
COLLECTIONS_NAMESPACE = "collections"
ARMATURES_NAMESPACE = "armatures"
ACTIONS_NAMESPACE = "actions"
IMAGES_NAMESPACE = "images"
LATTICES_NAMESPACE = "lattices"
NODETREES_NAMESPACE = "node_groups"
SCENES_NAMESPACE = "scenes"
TEXTS_NAMESPACE = "texts"
VOLUMES_NAMESPACE = "volumes"
WORLDS_NAMESPACE = "worlds"
SPEAKERS_NAMESPACE = "speakers"
GREASEPENCIL_NAMESPACE = "grease_pencils"


# --- V16: Centralized Type Mapping ---

# Maps Blender's `bl_rna.identifier` to our internal canonical type names.
# This is the SINGLE SOURCE OF TRUTH for normalizing types from the parser.
BLENDER_TO_FN_TYPE = {
    # Direct Mappings
    "Object": "OBJECT",
    "Mesh": "MESH",
    "Camera": "CAMERA",
    "Material": "MATERIAL",
    "Collection": "COLLECTION",
    "Curve": "CURVE",
    "Scene": "SCENE",
    "Armature": "ARMATURE",
    "Action": "ACTION",
    "Image": "IMAGE",
    "Lattice": "LATTICE",
    "NodeTree": "NODETREE",
    "Text": "TEXT",
    "Volume": "VOLUME",
    "World": "WORLD",
    "Speaker": "SPEAKER",
    "GreasePencil": "GREASEPENCIL",

    # Aliased Mappings (Different light types all become 'LIGHT')
    "Light": "LIGHT",
    "SunLight": "LIGHT",
    "PointLight": "LIGHT",
    "SpotLight": "LIGHT",
    "AreaLight": "LIGHT",
}

# Maps our internal canonical type names to the correct `bpy.data` collection name.
# This is the SINGLE SOURCE OF TRUTH for accessing Blender's data collections.
FN_TYPE_TO_BLENDER_COLLECTION = {
    "OBJECT": "objects",
    "MESH": "meshes",
    "LIGHT": "lights",
    "CAMERA": "cameras",
    "MATERIAL": "materials",
    "COLLECTION": "collections",
    "CURVE": "curves",
    "SCENE": "scenes",
    "WORLD": "worlds",
    "ARMATURE": "armatures",
    "ACTION": "actions",
    "IMAGE": "images",
    "LATTICE": "lattices",
    "NODETREE": "node_groups",
    "TEXT": "texts",
    "VOLUME": "volumes",
    "SPEAKER": "speakers",
    "GREASEPENCIL": "grease_pencils",
}

# A map from Blender's RNA identifiers to our canonical namespace names.
_TYPE_TO_NAMESPACE_MAP = {
    'OBJECT': OBJECTS_NAMESPACE,
    'MESH': MESHES_NAMESPACE,
    'LIGHT': LIGHTS_NAMESPACE,
    'MATERIAL': MATERIALS_NAMESPACE,
    'CAMERA': CAMERAS_NAMESPACE,
    'CURVE': CURVES_NAMESPACE,
    'COLLECTION': COLLECTIONS_NAMESPACE,
    'ARMATURE': ARMATURES_NAMESPACE,
    'ACTION': ACTIONS_NAMESPACE,
    'IMAGE': IMAGES_NAMESPACE,
    'LATTICE': LATTICES_NAMESPACE,
    'NODETREE': NODETREES_NAMESPACE,
    'SCENE': SCENES_NAMESPACE,
    'TEXT': TEXTS_NAMESPACE,
    'VOLUME': VOLUMES_NAMESPACE,
    'WORLD': WORLDS_NAMESPACE,
    'SPEAKER': SPEAKERS_NAMESPACE,
    'GREASEPENCIL': GREASEPENCIL_NAMESPACE,
}

def get_namespace_for_type(datablock_type: str) -> str | None:
    """
    Returns the correct, canonical namespace name for a given datablock type.

    Args:
        datablock_type: The uppercase RNA identifier (e.g., "MESH", "OBJECT").

    Returns:
        The canonical namespace name (e.g., "meshes") or None if not defined.
    """
    return _TYPE_TO_NAMESPACE_MAP.get(datablock_type)

