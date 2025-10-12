import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketString
from ..engine import utils, query_engine
from ..proxy_types import DatablockProxy
from .. import logger

class FN_set_collection(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_collection"
    bl_label = "Set Collection"

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('ADD', "Add", "Add objects to collections, creating the collections if they don't exist."),
            ('REMOVE', "Remove", "Remove objects from the specified collections."),
            ('CREATE', "Create", "Create new, empty collections, replacing any existing ones with the same name."),
        ],
        default='ADD',
    )

    link_mode: bpy.props.EnumProperty(
        name="Link Mode",
        items=[
            ('LINK', "Link", "Add objects to the collection, keeping existing memberships."),
            ('MOVE', "Move", "Move objects to the collection, removing them from all other collections."),
        ],
        default='LINK',
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketString', "Selection")
        self.inputs.new('FNSocketString', "Collection Names")
        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")
        if self.mode != 'REMOVE':
            layout.prop(self, "link_mode", text="")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        selection_string = kwargs.get("Selection")
        collection_names_str = kwargs.get("Collection Names")

        if not scene_root or not collection_names_str:
            return {self.outputs[0].identifier: scene_root}

        if not selection_string:
            selection_string = "*"

        new_scene_root = scene_root.clone()
        proxies_to_affect = query_engine.execute_query(new_scene_root, selection_string)
        collection_names = utils.parse_multi_target_string(collection_names_str)

        logger.log(f"[SetCollection] Affecting {len(proxies_to_affect)} proxies with collections: {collection_names} (Mode: {self.mode})")

        for name in collection_names:
            collections_namespace_path = f"{new_scene_root.path}/collections"
            collection_path = f"{collections_namespace_path}/{name}"
            collection_proxy = new_scene_root.find_child_by_path(collection_path)

            # Handle CREATE mode: unconditionally remove the old collection proxy if it exists.
            if self.mode == 'CREATE' and collection_proxy:
                logger.log(f"[SetCollection] Mode CREATE: Pruning existing collection '{collection_path}'")
                collection_proxy.prune()
                collection_proxy = None

            # Handle ADD or CREATE mode: ensure the collection proxy exists.
            if self.mode in ['CREATE', 'ADD'] and not collection_proxy:
                collections_namespace = new_scene_root.find_child_by_path(collections_namespace_path)
                if not collections_namespace:
                    collections_namespace = DatablockProxy(path=collections_namespace_path, parent=new_scene_root)
                
                logger.log(f"[SetCollection] Mode {self.mode}: Creating new collection proxy '{collection_path}'")
                uuid = self.get_persistent_uuid(f"coll_{name}")
                collection_proxy = DatablockProxy(path=collection_path, fn_uuid=uuid, parent=collections_namespace)
                collection_proxy.properties['datablock_type'] = 'COLLECTION'
                collection_proxy.properties['name'] = name

                # V17.10: Automatically link the new collection to the scene root to make it visible.
                scene_collection_rels = collection_proxy.properties.setdefault('_fn_relationships', {})
                scene_collection_links = scene_collection_rels.setdefault('collection_links', [])
                if new_scene_root.path not in scene_collection_links:
                    scene_collection_links.append(new_scene_root.path)

            # --- Membership Logic ---
            if self.mode in ['CREATE', 'ADD']:
                if not collection_proxy: continue
                for proxy in proxies_to_affect:
                    if proxy.properties.get('datablock_type') != 'OBJECT': continue
                    relationships = proxy.properties.setdefault('_fn_relationships', {})
                    links = relationships.setdefault('collection_links', [])
                    
                    if self.link_mode == 'MOVE':
                        links.clear()
                    
                    if collection_path not in links:
                        links.append(collection_path)
            
            elif self.mode == 'REMOVE':
                for proxy in proxies_to_affect:
                    if proxy.properties.get('datablock_type') != 'OBJECT': continue
                    if '_fn_relationships' in proxy.properties and 'collection_links' in proxy.properties['_fn_relationships']:
                        links = proxy.properties['_fn_relationships']['collection_links']
                        if collection_path in links:
                            links.remove(collection_path)
            
            # V17.13: Prune collection if it becomes orphaned after a REMOVE operation
            if self.mode == 'REMOVE' and collection_proxy:
                is_used = False
                for proxy in new_scene_root.get_flat_list():
                    if proxy.properties.get('datablock_type') != 'OBJECT': continue
                    if collection_path in proxy.properties.get('_fn_relationships', {}).get('collection_links', []):
                        is_used = True
                        break
                if not is_used:
                    logger.log(f"[SetCollection] Pruning orphaned collection '{collection_path}'")
                    collection_proxy.prune()

        return {self.outputs[0].identifier: new_scene_root}
