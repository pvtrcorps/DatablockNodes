import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketCollection, FNSocketObjectList, FNSocketCollectionList

class FN_link_to_collection(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_link_to_collection"
    bl_label = "Link to Collection"

    def init(self, context):
        FNBaseNode.init(self, context)
        # Clear existing inputs to re-add them in order
        while self.inputs:
            self.inputs.remove(self.inputs[-1])

        # The target collection datablock will be modified.
        collection_socket = self.inputs.new('FNSocketCollection', "Collection")
        collection_socket.is_mutable = True

        # The collection list socket is for reference only; the collections themselves are not changed.
        collections_socket = self.inputs.new('FNSocketCollectionList', "Collections")
        collections_socket.is_mutable = False
        collections_socket.display_shape = 'SQUARE'

        # The object list socket is for reference only; the objects themselves are not changed.
        objects_socket = self.inputs.new('FNSocketObjectList', "Objects")
        objects_socket.is_mutable = False
        objects_socket.display_shape = 'SQUARE'

        self.outputs.new('FNSocketCollection', "Collection")

    def draw_buttons(self, context, layout):
        pass

    def update_hash(self, hasher):
        # Hash the input Collection
        collection_input = self.inputs.get('Collection')
        if collection_input and collection_input.is_linked:
            # The reconciler will hash the upstream node's output.
            # We only need to hash the default value if unlinked.
            pass
        elif collection_input and hasattr(collection_input, 'default_value'):
            hasher.update(str(collection_input.default_value).encode())

        # Hash the input Collections list
        collections_input = self.inputs.get('Collections')
        if collections_input and collections_input.is_linked:
            pass
        elif collections_input and hasattr(collections_input, 'default_value'):
            hasher.update(str(collections_input.default_value).encode())

        # Hash the input Objects list
        objects_input = self.inputs.get('Objects')
        if objects_input and objects_input.is_linked:
            pass
        elif objects_input and hasattr(objects_input, 'default_value'):
            hasher.update(str(objects_input.default_value).encode())

    def execute(self, **kwargs):
        target_collection = kwargs.get(self.inputs['Collection'].identifier)
        collections_to_link = kwargs.get(self.inputs['Collections'].identifier)
        objects_to_link = kwargs.get(self.inputs['Objects'].identifier)

        tree = kwargs.get('tree')

        if not target_collection:
            print(f"  - Warning: No target collection provided to {self.name}. Skipping.")
            return None

        # Link collections
        if collections_to_link:
            if not isinstance(collections_to_link, list):
                collections_to_link = [collections_to_link]
            for col in collections_to_link:
                if col and isinstance(col, bpy.types.Collection):
                    if col.name not in target_collection.children:
                        target_collection.children.link(col)
                        print(f"  - Linked collection '{col.name}' to collection '{target_collection.name}'")
                        self._register_relationship(tree, col, target_collection, "COLLECTION_CHILD_LINK")
                    else:
                        print(f"  - Collection '{col.name}' already in collection '{target_collection.name}'")
                else:
                    print(f"  - Warning: An item provided to {self.name} (Collections) is not a valid collection. Skipping.")

        # Link objects
        if objects_to_link:
            if not isinstance(objects_to_link, list):
                objects_to_link = [objects_to_link]
            for obj in objects_to_link:
                if obj and isinstance(obj, bpy.types.Object):
                    # More robust check for target_collection validity
                    if obj.name not in target_collection.objects:
                        try:
                            target_collection.objects.link(obj)
                            print(f"  - Linked object '{obj.name}' to collection '{target_collection.name}'")
                            self._register_relationship(tree, obj, target_collection, "COLLECTION_OBJECT_LINK")
                        except AttributeError as e:
                            print(f"  - ERROR: Failed to link object '{obj.name}' to collection '{target_collection.name}'.")
                            print(f"    Reason: {e}")
                            print(f"    Type of target_collection: {type(target_collection)}")
                            print(f"    Type of target_collection.objects: {type(target_collection.objects)}")
                            print(f"    Please ensure the target collection is valid and accessible.")
                            print(f"    You may need to manually link the object in Blender's Outliner.")
                    else:
                        print(f"  - Object '{obj.name}' already in collection '{target_collection.name}'")
                else:
                    print(f"  - Warning: An item provided to {self.name} (Objects) is not a valid object. Skipping.")
        
        return {self.outputs[0].identifier: target_collection}

    def _register_relationship(self, tree, source_datablock, target_datablock, relationship_type):
        new_rel_item = tree.fn_relationships_map.add()
        new_rel_item.node_id = self.fn_node_id
        new_rel_item.source_uuid = uuid_manager.get_uuid(source_datablock)
        new_rel_item.target_uuid = uuid_manager.get_uuid(target_datablock)
        new_rel_item.relationship_type = relationship_type
        print(f"  - Debug: Registered relationship: {relationship_type} from {source_datablock.name} to {target_datablock.name}")
