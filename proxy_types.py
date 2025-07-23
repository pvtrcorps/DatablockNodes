import uuid
from copy import deepcopy

class DatablockProxy:
    """
    Represents a node in the scene graph (a "Prim"). It's a hierarchical structure
    that describes the desired state of a Blender datablock and its relationships.
    This is the core data structure that flows through the V5 node system.
    """
    def __init__(self, path, fn_uuid=None, properties=None, parent=None):
        self.fn_uuid = fn_uuid or uuid.uuid4()
        self.path = path
        self.parent = parent
        self.children = []
        self.properties = properties or {}

        if self.parent:
            # Automatically register with the parent upon creation
            self.parent.children.append(self)

    def clone(self):
        """
        Creates a deep copy of the entire proxy subtree starting from this node.
        Crucially, the UUID of the original prim is PRESERVED in the clone.
        This ensures that modifications downstream still refer to the same logical entity.
        """
        # Create a clone of the current node, PRESERVING the original UUID.
        cloned_node = DatablockProxy(
            path=self.path,
            fn_uuid=self.fn_uuid, # Preserve the UUID
            properties=deepcopy(self.properties)
        )

        # Recursively clone children and establish the new parent-child relationship
        for child in self.children:
            cloned_child = child.clone()
            cloned_child.parent = cloned_node
            cloned_node.children.append(cloned_child)

        return cloned_node

    def find_child_by_path(self, search_path):
        """
        Finds a descendant proxy by its relative or absolute path.
        - Absolute paths must start from the root of the current tree.
        - Relative paths are resolved from the current proxy.
        
        Examples:
        - find_child_by_path('/root/character/arm')  # Absolute
        - find_child_by_path('arm/hand')             # Relative
        - find_child_by_path('../head')              # Relative (up one level)
        """
        if not isinstance(search_path, str):
            return None

        # For absolute paths, we need to find the root of the tree first.
        if search_path.startswith('/'):
            root = self
            while root.parent:
                root = root.parent
            # If the root's path doesn't match the start of the search path, it's an error
            if not search_path.startswith(root.path):
                 return None
            # Strip the root path to make the search relative from the root
            search_path = search_path[len(root.path):].lstrip('/')
            if not search_path: # The path was just the root
                return root
            return root.find_child_by_path(search_path)

        # Process the relative path parts
        parts = search_path.split('/')
        current_node = self
        for part in parts:
            if not part: continue # Skip empty parts from double slashes

            if part == '..':
                current_node = current_node.parent
                if current_node is None:
                    return None  # Tried to go above the tree's root
                continue
            
            found_child = None
            for child in current_node.children:
                # The child's name is the last component of its full path
                child_name = child.path.split('/')[-1]
                if child_name == part:
                    found_child = child
                    break
            
            if found_child:
                current_node = found_child
            else:
                return None  # Path part not found
        
        return current_node

    def merge(self, other_root):
        """
        Merges another proxy tree into this one using deep merge semantics,
        inspired by Gaffer and USD composition.
        Properties from other_root (the override layer) take precedence.
        """
        # We only care about the children of the other_root, as the root itself
        # is just a container in this context.
        for other_child in other_root.children:
            # The child's name is its unique identifier at this level
            child_name = other_child.path.split('/')[-1]
            
            # Check if a prim with the same name exists at this level
            my_child_equivalent = self.find_child_by_path(child_name)

            if my_child_equivalent:
                # If it exists, merge its properties and then recurse.
                # Properties from other_child will overwrite those in my_child_equivalent.
                my_child_equivalent.properties.update(deepcopy(other_child.properties))
                my_child_equivalent.merge(other_child)
            else:
                # If it doesn't exist, clone the entire incoming branch and attach it.
                new_branch = other_child.clone()
                new_branch.parent = self
                self.children.append(new_branch)

    def __repr__(self):
        return f"<DatablockProxy(path='{self.path}', children={len(self.children)})>"

    def get_tree_representation(self, level=0):
        """Returns a string representing the tree structure for debugging."""
        # The name is the last part of the path
        name = self.path.split('/')[-1] or self.path
        indent = "  " * level
        tree_str = f"{indent}- {name} (Path: {self.path}, UUID: {self.fn_uuid})\n"
        for child in self.children:
            tree_str += child.get_tree_representation(level + 1)
        return tree_str

    def repath(self, new_parent_path):
        """ 
        Recursively re-paths the proxy and all its children to a new parent path.
        It also updates the relationship paths.
        """
        # 1. Re-path the current proxy
        original_name = self.path.split('/')[-1]
        original_full_path = self.path
        self.path = f"{new_parent_path}/{original_name}"

        # 2. Re-path all children recursively
        for child in self.children:
            child.repath(self.path)

        # 3. Update internal relationship paths
        if '_fn_relationships' in self.properties:
            for rel_type, target_value in self.properties['_fn_relationships'].items():
                # This handles both single string paths and lists of paths
                if isinstance(target_value, str) and target_value.startswith(original_full_path):
                    self.properties['_fn_relationships'][rel_type] = target_value.replace(original_full_path, self.path, 1)
                elif isinstance(target_value, list):
                    new_list = []
                    for path_in_list in target_value:
                        if path_in_list.startswith(original_full_path):
                            new_list.append(path_in_list.replace(original_full_path, self.path, 1))
                        else:
                            new_list.append(path_in_list)
                    self.properties['_fn_relationships'][rel_type] = new_list

    def get_flat_list(self):
        """Returns a flat list of all proxies in the subtree, including self."""
        flat_list = [self]
        for child in self.children:
            flat_list.extend(child.get_flat_list())
        return flat_list

