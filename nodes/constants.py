
# -*- coding: utf-8 -*-

# ===============================================================================================================================
#
#    - Lista de todos los tipos de datablocks que vamos a soportar en el addon
#    - Diccionario que mapea los datablocks a sus sockets
#
# ===============================================================================================================================

# -------------------------------------------------------------------------------------------------------------------------------
# LISTA DE DATABLOCKS
# -------------------------------------------------------------------------------------------------------------------------------
DATABLOCK_TYPES = [
    ('SCENE', 'Scene', 'Scene'),
    ('OBJECT', 'Object', 'Object'),
    ('COLLECTION', 'Collection', 'Collection'),
    ('MATERIAL', 'Material', 'Material'),
    ('MESH', 'Mesh', 'Mesh'),
    ('LIGHT', 'Light', 'Light'),
    ('CAMERA', 'Camera', 'Camera'),
    ('IMAGE', 'Image', 'Image'),
    ('NODETREE', 'Node Tree', 'Node Tree'),
    ('TEXT', 'Text', 'Text'),
    ('WORLD', 'World', 'World'),
    ('WORKSPACE', 'WorkSpace', 'WorkSpace'),
    ('ARMATURE', 'Armature', 'Armature'),
    ('ACTION', 'Action', 'Action'),
]

# -------------------------------------------------------------------------------------------------------------------------------
# MAPEO DE DATABLOCKS A SOCKETS
# -------------------------------------------------------------------------------------------------------------------------------
DATABLOCK_SOCKET_MAP = {
    'SCENE': 'FNSocketScene',
    'OBJECT': 'FNSocketObject',
    'COLLECTION': 'FNSocketCollection',
    'MATERIAL': 'FNSocketMaterial',
    'MESH': 'FNSocketMesh',
    'LIGHT': 'FNSocketLight',
    'CAMERA': 'FNSocketCamera',
    'IMAGE': 'FNSocketImage',
    'NODETREE': 'FNSocketNodeTree',
    'TEXT': 'FNSocketText',
    'WORLD': 'FNSocketWorld',
    'WORKSPACE': 'FNSocketWorkSpace',
    'ARMATURE': 'FNSocketArmature',
    'ACTION': 'FNSocketAction',
}
