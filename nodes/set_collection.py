import bpy
from ..nodes.base import FNBaseNode
from ..sockets import FNSocketScene, FNSocketSelection, FNSocketString
from ..engine import utils
from ..proxy_types import DatablockProxy
from ..query_types import FNSelectionQuery
from .. import logger

def get_all_prims(root_proxy):
    all_prims = []
    nodes_to_visit = [root_proxy]
    while nodes_to_visit:
        node = nodes_to_visit.pop(0)
        all_prims.append(node)
        nodes_to_visit.extend(node.children)
    return all_prims

class FN_set_collection(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_collection"
    bl_label = "Set Collection"

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('ADD', "Add", "Add prims to the collection(s). Creates them if they don't exist."),
            ('REMOVE', "Remove", "Remove prims from the collection(s)."),
            ('CREATE', "Create", "Create new collection(s), replacing any existing ones with the same name."),
        ],
        default='ADD',
    )

    link_mode: bpy.props.EnumProperty(
        name="Link Mode",
        items=[
            ('LINK', "Link", "Add prims to the new collection, keeping existing collection memberships."),
            ('MOVE', "Move", "Move prims to the new collection, removing them from all other collections."),
        ],
        default='LINK',
    )

    link_to_scene: bpy.props.BoolProperty(
        name="Link to Scene",
        description="Ensure the collection itself is linked to the scene's root collection.",
        default=True
    )

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketScene', "Scene")
        self.inputs.new('FNSocketSelection', "Selection")
        self.inputs.new('FNSocketString', "Collection Names")
        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        layout.prop(self, "mode", text="")
        if self.mode != 'REMOVE':
            layout.prop(self, "link_mode", text="")
        layout.prop(self, "link_to_scene")

    def execute(self, **kwargs):
        scene_root = kwargs.get("Scene")
        selection_query = kwargs.get("Selection")
        collection_names_str = kwargs.get("Collection Names")

        logger.log(f"[SetCollection] Mode: {self.mode}, Link Mode: {self.link_mode}")
        logger.log(f"[SetCollection] Input Collections: {collection_names_str}")

        if not scene_root or not collection_names_str:
            return {self.outputs[0].identifier: scene_root}

        if not selection_query:
            selection_query = FNSelectionQuery(raw_expression="*", path_glob="*", filters=[])

        new_scene_root = scene_root.clone()
        prims_to_affect = [p for p in utils.resolve_selection(new_scene_root, selection_query) if p.parent is not None]
        collection_names = utils.parse_multi_target_string(collection_names_str)

        logger.log(f"[SetCollection] Prims to affect: {[p.path for p in prims_to_affect]}")

        for name in collection_names:
            collection_path = f"/{name}"
            collection_prim = new_scene_root.find_child_by_path(collection_path)
            logger.log(f"[SetCollection] Processing '{name}'. Exists: {collection_prim is not None}")

            # CREATE mode: Unconditionally remove the old collection prim if it exists.
            if self.mode == 'CREATE' and collection_prim:
                logger.log(f"[SetCollection] CREATE: Removing existing collection prim '{name}'")
                # Remove any links pointing to the old collection
                for p in get_all_prims(new_scene_root):
                    links = p.properties.get('_fn_relationships', {}).get('collection_links', [])
                    if collection_path in links:
                        links.remove(collection_path)
                # Remove the prim itself
                if collection_prim.parent:
                    collection_prim.parent.children.remove(collection_prim)
                collection_prim = None

            # ADD or CREATE mode: Ensure the collection prim exists.
            if self.mode in ['CREATE', 'ADD'] and not collection_prim:
                logger.log(f"[SetCollection] {self.mode}: Creating new collection prim '{name}'")
                uuid = self.get_persistent_uuid(f"coll_{name}")
                collection_prim = DatablockProxy(path=collection_path, fn_uuid=uuid)
                collection_prim.properties['datablock_type'] = 'COLLECTION'
                collection_prim.properties['name'] = name
                new_scene_root.children.append(collection_prim) # Explicitly add to children

            # Link prims based on the mode
            if self.mode in ['CREATE', 'ADD'] and collection_prim:
                logger.log(f"[SetCollection] Linking {len(prims_to_affect)} prims to '{name}'")
                for prim in prims_to_affect:
                    relationships = prim.properties.setdefault('_fn_relationships', {})
                    links = relationships.setdefault('collection_links', [])
                    
                    if self.link_mode == 'MOVE':
                        logger.log(f"[SetCollection] MOVE: Clearing existing links for {prim.path}")
                        links.clear()
                    
                    if collection_path not in links:
                        links.append(collection_path)
            
            elif self.mode == 'REMOVE' and collection_prim:
                logger.log(f"[SetCollection] Removing {len(prims_to_affect)} prims from '{name}'")
                for prim in prims_to_affect:
                    links = prim.properties.get('_fn_relationships', {}).get('collection_links', [])
                    if collection_path in links:
                        links.remove(collection_path)
            
            # Ensure the collection itself is linked to the scene's root collection if link_to_scene is True
            if self.link_to_scene and collection_prim:
                relationships = collection_prim.properties.setdefault('_fn_relationships', {})
                links = relationships.setdefault('collection_links', [])
                if '/root' not in links:
                    links.append('/root')

        logger.log(f"[SetCollection] Final scene graph:\n{new_scene_root.get_tree_representation()}")
        return {self.outputs[0].identifier: new_scene_root}
