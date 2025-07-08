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

    def execute(self, **kwargs):
        target_collection = kwargs.get(self.inputs['Collection'].identifier)
        collections_to_link = kwargs.get(self.inputs['Collections'].identifier)
        objects_to_link = kwargs.get(self.inputs['Objects'].identifier)

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
                    if obj.name not in target_collection.objects:
                        target_collection.objects.link(obj)
                        print(f"  - Linked object '{obj.name}' to collection '{target_collection.name}'")
                    else:
                        print(f"  - Object '{obj.name}' already in collection '{target_collection.name}'")
                else:
                    print(f"  - Warning: An item provided to {self.name} (Objects) is not a valid object. Skipping.")
        
        return {self.outputs[0].identifier: target_collection}
