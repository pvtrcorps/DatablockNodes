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

    manages_scene_datablock: bpy.props.BoolProperty(
        name="Manages Scene Datablock",
        description="Controls whether this node can directly affect the Blender scene, thus showing the activate button.",
        default=True
    )

    def init(self, context):
        """Assign a unique ID when the node is created."""
        if not self.fn_node_id:
            self.fn_node_id = str(uuid.uuid4())

    def copy(self, node):
        """Ensure a new UUID is generated when the node is duplicated."""
        self.fn_node_id = str(uuid.uuid4())

    def execute(self, tree: bpy.types.NodeTree, execution_cache: dict) -> tuple[dict, dict]:
        """Executes the node's logic and updates the execution cache.
        This method should be overridden by subclasses.
        Returns a tuple: (result_dict, visibility_flags_dict)
        """
        return {}, {}

    def _trigger_update(self, context):
        """A generic update function to be used by properties that should trigger tree execution."""
        self.id_data.update_tag()

    def update_hash(self, hasher):
        """Updates the hash with the node's internal properties.
        Subclasses should override this to include their specific properties.
        """
        # Add the node's own ID and bl_idname to the hash to make it unique and type-specific
        hasher.update(self.fn_node_id.encode())
        hasher.update(self.bl_idname.encode())

    
