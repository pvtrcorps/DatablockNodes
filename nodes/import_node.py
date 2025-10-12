
"""
Imports a .blend file by parsing one of its scenes into a DatablockProxy hierarchy.
"""

import bpy
import os
import json
import hashlib
from pathlib import Path
import subprocess

from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString, FNSocketBool
from ..proxy_types import DatablockProxy
from .. import logger

class FN_import_node(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_import_node"
    bl_label = "Import"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "File Path").subtype = 'FILE_PATH'
        self.inputs.new('FNSocketString', "Scene Name").default_value = ""
        self.inputs.new('FNSocketBool', "Force Rebuild").default_value = False
        self.outputs.new('FNSocketScene', "Scene")

    def _trigger_update(self, context):
        self.id_data.update_tag()

    def calculate_file_hash(self, file_path):
        logger.log(f"[ImportNode] Calculating hash for: {file_path}")
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            hash_value = hasher.hexdigest()
            logger.log(f"[ImportNode]  -> Hash: {hash_value}")
            return hash_value
        except IOError as e:
            logger.log(f"Could not read file for hashing: {e}", level='ERROR')
            return None

    def launch_blend_parser(self, file_path, cache_path):
        logger.log("[ImportNode] Launching blend parser...")
        blender_executable = bpy.app.binary_path
        parser_script_path = Path(__file__).parent.parent / "engine" / "blend_parser.py"

        if not blender_executable or not parser_script_path.exists():
            logger.log(f"Blender executable or parser script not found.", level='ERROR')
            logger.log(f"           Blender: {blender_executable}")
            logger.log(f"           Parser: {parser_script_path}")
            return

        command = [
            str(blender_executable),
            "--background",
            str(file_path),
            "--python",
            str(parser_script_path),
            "--",
            "--output",
            str(cache_path)
        ]
        logger.log(f"[ImportNode]  -> Command: {' '.join(command)}")
        try:
            # Use subprocess.run to make the call blocking and wait for it to complete.
            # This makes the user flow synchronous and predictable.
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            logger.log("[ImportNode]  -> Parser process finished.")
            if result.stdout:
                logger.log(f"[ImportNode]  -> Parser STDOUT:\n--- START ---\n{result.stdout}--- END ---")
            if result.stderr:
                logger.log(f"[ImportNode]  -> Parser STDERR:\n--- START ---\n{result.stderr}--- END ---")

        except subprocess.CalledProcessError as e:
            logger.log(f"Parser process failed with exit code {e.returncode}", level='ERROR')
            logger.log(f"[ImportNode]  -> Parser STDERR:\n--- START ---\n{e.stderr}--- END ---")
        except Exception as e:
            logger.log(f"Failed to launch background process: {e}", level='ERROR')

    def load_proxy_from_cache(self, cache_path, scene_name):
        logger.log(f"[ImportNode] Loading from cache: {cache_path}")
        if not os.path.exists(cache_path):
            logger.log("Cache file does not exist.", level='ERROR')
            return None
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            # --- V15 Architecture: Unified Cache Logic ---
            if scene_name:
                # Mode 1: Load a specific scene from the 'scenes' dictionary.
                logger.log(f"[ImportNode]  -> Scene Mode: Loading ''{scene_name}'' from cache.")
                proxy_data = data.get("scenes", {}).get(scene_name)
                if not proxy_data:
                    logger.log(f"Scene ''{scene_name}'' not found in cache file.", level='ERROR')
                    return None
            else:
                # Mode 2: Load the entire file as a library from the 'library' dictionary.
                logger.log("[ImportNode]  -> Library Mode: Loading full library from cache.")
                proxy_data = data.get("library")
                if not proxy_data:
                    logger.log("'library' section not found in cache file.", level='ERROR')
                    return None

            return DatablockProxy.from_dict(proxy_data)

        except (json.JSONDecodeError, IOError) as e:
            logger.log(f"Failed to read or parse cache file: {e}", level='ERROR')
            return None

    def execute(self, **kwargs):
        logger.log("--- Import Node Execution --- ")
        file_path_str = kwargs.get("File Path")
        scene_name = kwargs.get("Scene Name")
        force_rebuild = kwargs.get("Force Rebuild")

        if not file_path_str or not os.path.exists(file_path_str):
            logger.log("Aborting: File Path is not set or file does not exist.", level='WARNING')
            return {self.outputs[0].identifier: None}

        file_path = Path(file_path_str)
        cache_path = file_path.with_suffix(file_path.suffix + ".fn_cache.json")
        logger.log(f"[ImportNode] Source file: {file_path}")
        logger.log(f"[ImportNode] Cache file: {cache_path}")

        source_hash = self.calculate_file_hash(file_path)
        if not source_hash:
            return {self.outputs[0].identifier: None}

        is_cache_valid = False
        if cache_path.exists() and not force_rebuild:
            logger.log("[ImportNode] Cache file exists. Checking validity...")
            try:
                with open(cache_path, 'r') as f:
                    metadata = json.load(f).get("metadata", {})
                if metadata.get("source_hash") == source_hash:
                    is_cache_valid = True
                    logger.log("[ImportNode]  -> Cache is VALID.")
                else:
                    logger.log("[ImportNode]  -> Cache is OUTDATED (hash mismatch).")
            except (json.JSONDecodeError, IOError) as e:
                logger.log(f"Cache is CORRUPTED ({e}).", level='WARNING')
                is_cache_valid = False
        else:
            logger.log("[ImportNode] Cache does not exist or rebuild is forced.")

        if not is_cache_valid:
            logger.log("[ImportNode] Rebuilding cache...")
            self.bl_label = f"Import (Parsing...)"
            self.launch_blend_parser(file_path, cache_path)
            # After parsing, the cache is now valid, so we can proceed.
            logger.log("[ImportNode] Cache rebuilt. Proceeding to load.")

        self.bl_label = "Import"
        logger.log("[ImportNode] Loading proxy from cache.")
        root_proxy = self.load_proxy_from_cache(cache_path, scene_name)
        
        if root_proxy:
            logger.log(f"[ImportNode] Successfully loaded root proxy: {root_proxy.path}")
            
            # --- V18: Make all imported collections procedural ---
            logger.log("[ImportNode] Converting all imported collections to procedural.")
            collections_converted = 0
            for proxy in root_proxy.get_flat_list():
                if proxy.properties.get('datablock_type') == 'COLLECTION':
                    proxy.properties['_fn_source'] = {'type': 'procedural'}
                    collections_converted += 1
            logger.log(f"[ImportNode] Converted {collections_converted} collections to procedural.")
        else:
            logger.log("[ImportNode] Failed to load root proxy from cache.")

        logger.log("--- Import Node Finished ---")
        return {self.outputs[0].identifier: root_proxy}
