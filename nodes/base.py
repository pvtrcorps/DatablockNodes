import bpy
import uuid

class FNBaseNode(bpy.types.Node):
    """Base class for all File Nodes, providing the persistent UUID."""
    
    # This property will store the persistent ID for each node.
    fn_node_id: bpy.props.StringProperty(
        name="Node ID",
        description="Persistent identifier for the node, used for state tracking.",
        default="",
    )

    def init(self, context):
        """Assign a unique ID when the node is created."""
        if not self.fn_node_id:
            self.fn_node_id = str(uuid.uuid4())

    def copy(self, node):
        """Ensure a new UUID is generated when the node is duplicated."""
        self.fn_node_id = str(uuid.uuid4())

    def execute(self, tree: bpy.types.NodeTree, execution_cache: dict):
        """Executes the node's logic and updates the execution cache.
        This method should be overridden by subclasses.
        """
        pass

    
