import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketObject, FNSocketObjectList

class FN_set_object_parent(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_object_parent"
    bl_label = "Set Object Parent"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketObject', "Parent")
        self.inputs.new('FNSocketObjectList', "Childs").is_mutable = True
        self.inputs['Childs'].display_shape = 'SQUARE'

        self.outputs.new('FNSocketObjectList', "Parent and Childs").is_mutable = False
        self.outputs['Parent and Childs'].display_shape = 'SQUARE'

    def draw_buttons(self, context, layout):
        pass

    def update_hash(self, hasher):
        parent_input = self.inputs.get('Parent')
        if parent_input and parent_input.is_linked:
            pass
        elif parent_input and hasattr(parent_input, 'default_value'):
            hasher.update(str(parent_input.default_value).encode())

        childs_input = self.inputs.get('Childs')
        if childs_input and childs_input.is_linked:
            pass
        elif childs_input and hasattr(childs_input, 'default_value'):
            hasher.update(str(childs_input.default_value).encode())

    def execute(self, **kwargs):
        parent_obj = kwargs.get(self.inputs['Parent'].identifier)
        child_objects = kwargs.get(self.inputs['Childs'].identifier)
        tree = kwargs.get('tree')

        if not child_objects:
            print(f"  - Warning: No child objects provided to {self.name}. Skipping.")
            return {self.outputs[0].identifier: []}

        if not isinstance(child_objects, list):
            child_objects = [child_objects]

        processed_childs = []
        for child_obj in child_objects:
            if not child_obj or not isinstance(child_obj, bpy.types.Object):
                print(f"  - Warning: Invalid child object provided to {self.name}. Skipping.")
                continue

            # Clear existing parent if no parent_obj is provided
            if not parent_obj:
                if child_obj.parent:
                    child_obj.parent = None
                    print(f"  - Cleared parent of object '{child_obj.name}'")
                
                # Remove any existing OBJECT_PARENTING relationships for this child
                relationships_to_remove_indices = []
                for i, rel_item in enumerate(tree.fn_relationships_map):
                    if rel_item.node_id == self.fn_node_id and rel_item.source_uuid == uuid_manager.get_uuid(child_obj) and rel_item.relationship_type == "OBJECT_PARENTING":
                        relationships_to_remove_indices.append(i)
                
                for i in sorted(relationships_to_remove_indices, reverse=True):
                    tree.fn_relationships_map.remove(i)

            elif isinstance(parent_obj, bpy.types.Object):
                if child_obj.parent != parent_obj:
                    child_obj.parent = parent_obj
                    print(f"  - Set parent of object '{child_obj.name}' to '{parent_obj.name}'")
                else:
                    print(f"  - Object '{child_obj.name}' already parented to '{parent_obj.name}'")
                
                # Register relationship
                new_rel_item = tree.fn_relationships_map.add()
                new_rel_item.node_id = self.fn_node_id
                new_rel_item.source_uuid = uuid_manager.get_uuid(child_obj)
                new_rel_item.target_uuid = uuid_manager.get_uuid(parent_obj)
                new_rel_item.relationship_type = "OBJECT_PARENTING"
            else:
                print(f"  - Warning: Invalid parent object provided to {self.name}. Skipping parenting.")
            
            processed_childs.append(child_obj)

        output_list = []
        if parent_obj:
            output_list.append(parent_obj)
        output_list.extend(processed_childs)

        return {self.outputs[0].identifier: output_list}
