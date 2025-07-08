
import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketScene, FNSocketObjectList, FNSocketCollectionList

class FN_link_to_scene(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_link_to_scene"
    bl_label = "Link to Scene"

    def init(self, context):
        FNBaseNode.init(self, context)
        # Clear existing inputs to re-add them in order
        while self.inputs:
            self.inputs.remove(self.inputs[-1])

        # The scene datablock will be modified (an object/collection will be linked to it).
        scene_socket = self.inputs.new('FNSocketScene', "Scene")
        scene_socket.is_mutable = True

        # The collection list socket is for reference only; the collections themselves are not changed.
        collections_socket = self.inputs.new('FNSocketCollectionList', "Collections")
        collections_socket.is_mutable = False
        collections_socket.display_shape = 'SQUARE'

        # The object list socket is for reference only; the objects themselves are not changed.
        objects_socket = self.inputs.new('FNSocketObjectList', "Objects")
        objects_socket.is_mutable = False
        objects_socket.display_shape = 'SQUARE'

        self.outputs.new('FNSocketScene', "Scene")

    def draw_buttons(self, context, layout):
        pass

    def execute(self, **kwargs):
        target_scene = kwargs.get(self.inputs['Scene'].identifier)
        collections_to_link = kwargs.get(self.inputs['Collections'].identifier)
        objects_to_link = kwargs.get(self.inputs['Objects'].identifier)

        if not target_scene:
            print(f"  - Warning: No target scene provided to {self.name}. Skipping.")
            return None

        # Link collections
        if collections_to_link:
            if not isinstance(collections_to_link, list):
                collections_to_link = [collections_to_link]
            for col in collections_to_link:
                if col and isinstance(col, bpy.types.Collection):
                    if col.name not in target_scene.collection.children:
                        target_scene.collection.children.link(col)
                        print(f"  - Linked collection '{col.name}' to scene '{target_scene.name}'")
                    else:
                        print(f"  - Collection '{col.name}' already in scene '{target_scene.name}'")
                else:
                    print(f"  - Warning: An item provided to {self.name} (Collections) is not a valid collection. Skipping.")

        # Link objects
        if objects_to_link:
            if not isinstance(objects_to_link, list):
                objects_to_link = [objects_to_link]
            for obj in objects_to_link:
                if obj and isinstance(obj, bpy.types.Object):
                    if obj.name not in target_scene.collection.objects:
                        target_scene.collection.objects.link(obj)
                        print(f"  - Linked object '{obj.name}' to scene '{target_scene.name}'")
                    else:
                        print(f"  - Object '{obj.name}' already in scene '{target_scene.name}'")
                else:
                    print(f"  - Warning: An item provided to {self.name} (Objects) is not a valid object. Skipping.")
        
        return {self.outputs[0].identifier: target_scene}
