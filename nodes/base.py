import bpy
import uuid
import hashlib

class FNBaseNode(bpy.types.Node):
    """Base class for all File Nodes, providing the persistent UUID."""
    
    # This property will store the persistent ID for each node.
    fn_node_id: bpy.props.StringProperty(
        name="Node ID",
        description="Persistent identifier for the node, used for state tracking.",
        default="",
    )

    # This property will store the persistent UUID for the datablock declared by this node.
    fn_output_uuid: bpy.props.StringProperty(
        name="Output Datablock UUID",
        description="Persistent UUID for the datablock generated by this node.",
        default="",
    )

    manages_scene_datablock: bpy.props.BoolProperty(
        name="Manages Scene Datablock",
        description="Controls whether this node can directly affect the Blender scene, thus showing the activate button.",
        default=True
    )

    def init(self, context):
        """Assign a unique ID when the node is created."""
        if not self.fn_node_id:
            self.fn_node_id = str(uuid.uuid4())
        if not self.fn_output_uuid:
            self.fn_output_uuid = str(uuid.uuid4())

    def copy(self, node):
        """Ensure a new UUID is generated when the node is duplicated."""
        self.fn_node_id = str(uuid.uuid4())
        self.fn_output_uuid = str(uuid.uuid4())

    def get_persistent_uuid(self, identifier: str):
        """Generates a deterministic UUID for a part of the node."""
        return str(uuid.uuid5(uuid.UUID(self.fn_node_id), identifier))

    def execute(self, tree: bpy.types.NodeTree, execution_cache: dict) -> tuple[dict, dict]:
        """Executes the node's logic and updates the execution cache.
        This method should be overridden by subclasses.
        Returns a tuple: (result_dict, visibility_flags_dict)
        """
        return {}, {}

    def _trigger_update(self, context):
        """A generic update function to be used by properties that should trigger tree execution."""
        self.id_data.update_tag()

    

    
