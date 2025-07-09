import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketObject, FNSocketMaterial

class FN_set_object_material(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_object_material"
    bl_label = "Set Object Material"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketObject', "Object").is_mutable = True
        self.inputs.new('FNSocketMaterial', "Material")

        self.outputs.new('FNSocketObject', "Object")

    def draw_buttons(self, context, layout):
        pass

    def update_hash(self, hasher):
        object_input = self.inputs.get('Object')
        if object_input and object_input.is_linked:
            pass
        elif object_input and hasattr(object_input, 'default_value'):
            hasher.update(str(object_input.default_value).encode())

        material_input = self.inputs.get('Material')
        if material_input and material_input.is_linked:
            pass
        elif material_input and hasattr(material_input, 'default_value'):
            hasher.update(str(material_input.default_value).encode())

    def execute(self, **kwargs):
        obj = kwargs.get(self.inputs['Object'].identifier)
        material = kwargs.get(self.inputs['Material'].identifier)
        tree = kwargs.get('tree')

        if not obj or not isinstance(obj, bpy.types.Object):
            print(f"  - Warning: No valid object provided to {self.name}. Skipping.")
            return None

        # Clear existing material slots if no material is provided
        if not material:
            if obj.data and hasattr(obj.data, 'materials'):
                for i in range(len(obj.data.materials)):
                    obj.data.materials.pop(index=0)
                print(f"  - Cleared all materials from object '{obj.name}'")
            
            # Remove any existing OBJECT_MATERIAL_ASSIGN relationships for this object
            relationships_to_remove_indices = []
            for i, rel_item in enumerate(tree.fn_relationships_map):
                if rel_item.node_id == self.fn_node_id and rel_item.source_uuid == uuid_manager.get_uuid(obj) and rel_item.relationship_type == "OBJECT_MATERIAL_ASSIGN":
                    relationships_to_remove_indices.append(i)
            
            for i in sorted(relationships_to_remove_indices, reverse=True):
                tree.fn_relationships_map.remove(i)
            
            return {self.outputs[0].identifier: obj}

        if obj.data and isinstance(material, bpy.types.Material):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(material)
                print(f"  - Assigned material '{material.name}' to object '{obj.name}'")
            elif obj.data.materials[0] != material:
                obj.data.materials[0] = material
                print(f"  - Replaced material of object '{obj.name}' with '{material.name}'")
            else:
                print(f"  - Material '{material.name}' already assigned to object '{obj.name}'")
            
            # Register relationship
            new_rel_item = tree.fn_relationships_map.add()
            new_rel_item.node_id = self.fn_node_id
            new_rel_item.source_uuid = uuid_manager.get_uuid(obj)
            new_rel_item.target_uuid = uuid_manager.get_uuid(material)
            new_rel_item.relationship_type = "OBJECT_MATERIAL_ASSIGN"
        else:
            print(f"  - Warning: Invalid material or object data for {self.name}. Skipping material assignment.")

        return {self.outputs[0].identifier: obj}
