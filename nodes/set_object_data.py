import bpy
from ..nodes.base import FNBaseNode
from .. import uuid_manager
from ..sockets import FNSocketObject, FNSocketMesh, FNSocketArmature, FNSocketLight, FNSocketCamera

class FN_set_object_data(FNBaseNode, bpy.types.Node):
    bl_idname = "FN_set_object_data"
    bl_label = "Set Object Data"

    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketObject', "Object").is_mutable = True
        self.inputs.new('FNSocketMesh', "Mesh")
        self.inputs.new('FNSocketArmature', "Armature")
        self.inputs.new('FNSocketLight', "Light")
        self.inputs.new('FNSocketCamera', "Camera")

        self.outputs.new('FNSocketObject', "Object")

    def draw_buttons(self, context, layout):
        pass

    def update_hash(self, hasher):
        # Hash the input Object
        object_input = self.inputs.get('Object')
        if object_input and object_input.is_linked:
            pass
        elif object_input and hasattr(object_input, 'default_value'):
            hasher.update(str(object_input.default_value).encode())

        # Hash the input Data (Mesh, Armature, Light, Camera)
        for socket_name in ["Mesh", "Armature", "Light", "Camera"]:
            data_input = self.inputs.get(socket_name)
            if data_input and data_input.is_linked:
                pass
            elif data_input and hasattr(data_input, 'default_value'):
                hasher.update(str(data_input.default_value).encode())

    def execute(self, **kwargs):
        obj = kwargs.get(self.inputs['Object'].identifier)
        mesh_data = kwargs.get(self.inputs['Mesh'].identifier)
        armature_data = kwargs.get(self.inputs['Armature'].identifier)
        light_data = kwargs.get(self.inputs['Light'].identifier)
        camera_data = kwargs.get(self.inputs['Camera'].identifier)
        tree = kwargs.get('tree')

        if not obj or not isinstance(obj, bpy.types.Object):
            print(f"  - Warning: No valid object provided to {self.name}. Skipping.")
            return None

        new_data = None
        relationship_type = None

        if mesh_data and isinstance(mesh_data, bpy.types.Mesh):
            new_data = mesh_data
            relationship_type = "OBJECT_DATA_ASSIGN_MESH"
        elif armature_data and isinstance(armature_data, bpy.types.Armature):
            new_data = armature_data
            relationship_type = "OBJECT_DATA_ASSIGN_ARMATURE"
        elif light_data and isinstance(light_data, bpy.types.Light):
            new_data = light_data
            relationship_type = "OBJECT_DATA_ASSIGN_LIGHT"
        elif camera_data and isinstance(camera_data, bpy.types.Camera):
            new_data = camera_data
            relationship_type = "OBJECT_DATA_ASSIGN_CAMERA"
        
        if new_data:
            obj.data = new_data
            print(f"  - Set data of object '{obj.name}' to '{new_data.name}' ({type(new_data).__name__})")
            
            # Register relationship
            new_rel_item = tree.fn_relationships_map.add()
            new_rel_item.node_id = self.fn_node_id
            new_rel_item.source_uuid = uuid_manager.get_uuid(obj)
            new_rel_item.target_uuid = uuid_manager.get_uuid(new_data)
            new_rel_item.relationship_type = relationship_type
        else:
            # If no data is provided, set object.data to None and remove any existing relationship
            if obj.data is not None:
                print(f"  - Clearing data of object '{obj.name}'")
                obj.data = None
            
            # Remove any existing OBJECT_DATA_ASSIGN relationships for this object
            relationships_to_remove_indices = []
            for i, rel_item in enumerate(tree.fn_relationships_map):
                if rel_item.node_id == self.fn_node_id and rel_item.source_uuid == uuid_manager.get_uuid(obj) and rel_item.relationship_type.startswith("OBJECT_DATA_ASSIGN"):
                    relationships_to_remove_indices.append(i)
            
            for i in sorted(relationships_to_remove_indices, reverse=True):
                tree.fn_relationships_map.remove(i)

        return {self.outputs[0].identifier: obj}
