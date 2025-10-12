import uuid
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, Dict, Iterable, List, Union
from . import logger
from .engine import constants


class RelationshipType(Enum):
    PARENT = "parent"
    OBJECT_DATA = "data"
    COLLECTION_LINK = "collection_link"
    ACTIVE_MATERIAL = "active_material"
    SCENE_CAMERA = "camera"
    SCENE_WORLD = "world"


RELATIONSHIP_ALIASES: Dict[str, RelationshipType] = {
    "parent": RelationshipType.PARENT,
    "data": RelationshipType.OBJECT_DATA,
    "object_data": RelationshipType.OBJECT_DATA,
    "collection_link": RelationshipType.COLLECTION_LINK,
    "collection_links": RelationshipType.COLLECTION_LINK,
    "active_material": RelationshipType.ACTIVE_MATERIAL,
    "camera": RelationshipType.SCENE_CAMERA,
    "scene_camera": RelationshipType.SCENE_CAMERA,
    "world": RelationshipType.SCENE_WORLD,
    "scene_world": RelationshipType.SCENE_WORLD,
}


def resolve_relationship_type(identifier: Optional[str]) -> Optional[RelationshipType]:
    if not identifier:
        return None
    return RELATIONSHIP_ALIASES.get(str(identifier).lower())


@dataclass
class Relationship:
    type: RelationshipType
    target_uuid: str

    def to_dict(self) -> Dict[str, str]:
        return {"type": self.type.value, "target_uuid": self.target_uuid}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['Relationship']:
        rel_type = resolve_relationship_type(data.get("type"))
        target_uuid = data.get("target_uuid")
        if not rel_type or not target_uuid:
            return None
        return cls(type=rel_type, target_uuid=str(target_uuid))

class DatablockProxy:
    """
    Represents a node in the scene graph (a "Prim"). It's a hierarchical structure
    that describes the desired state of a Blender datablock and its relationships.
    This is the core data structure that flows through the V5 node system.
    """
    def __init__(self, path: str, fn_uuid: Optional[uuid.UUID] = None, properties: Optional[Dict[str, Any]] = None, parent: Optional['DatablockProxy'] = None):
        self.fn_uuid = fn_uuid or uuid.uuid4()
        self.path = path
        self.parent = parent
        self.children: List['DatablockProxy'] = []
        self.properties = properties or {}

        if self.parent:
            # Automatically register with the parent upon creation
            self.parent.children.append(self)

    def _upgrade_legacy_relationships(self, legacy: Dict[str, Any]) -> List[Relationship]:
        upgraded: List[Relationship] = []
        root = self.get_root()

        for key, target_value in legacy.items():
            rel_type = resolve_relationship_type(key)
            if not rel_type:
                continue

            values: Iterable[Any]
            if isinstance(target_value, list):
                values = target_value
            else:
                values = [target_value]

            for value in values:
                target_uuid: Optional[str] = None

                if isinstance(value, uuid.UUID):
                    target_uuid = str(value)
                elif isinstance(value, str):
                    target_proxy = root.find_child_by_path(value)
                    if not target_proxy:
                        logger.log(
                            f"[DatablockProxy] Could not resolve legacy relationship target '{value}' for '{self.path}'",
                            level='WARNING'
                        )
                        continue
                    target_uuid = str(target_proxy.fn_uuid)
                elif isinstance(value, dict):
                    potential_uuid = value.get('target_uuid')
                    if potential_uuid:
                        target_uuid = str(potential_uuid)

                if not target_uuid:
                    continue

                if not any(r.type == rel_type and r.target_uuid == target_uuid for r in upgraded):
                    upgraded.append(Relationship(rel_type, target_uuid))

        return upgraded

    def _ensure_relationship_list(self) -> List[Relationship]:
        relationships = self.properties.get('_fn_relationships')
        if relationships is None:
            relationships = []
            self.properties['_fn_relationships'] = relationships
        elif isinstance(relationships, dict):
            relationships = self._upgrade_legacy_relationships(relationships)
            self.properties['_fn_relationships'] = relationships
        elif isinstance(relationships, list):
            converted: List[Relationship] = []
            for entry in relationships:
                if isinstance(entry, Relationship):
                    converted.append(entry)
                elif isinstance(entry, dict):
                    rel = Relationship.from_dict(entry)
                    if rel:
                        converted.append(rel)
            relationships = converted
            self.properties['_fn_relationships'] = relationships
        return relationships

    def get_relationships(self) -> List[Relationship]:
        return self._ensure_relationship_list()

    def get_relationships_by_type(self, rel_type: RelationshipType) -> List[Relationship]:
        return [rel for rel in self.get_relationships() if rel.type == rel_type]

    def get_relationship_target_uuids(self, rel_type: RelationshipType) -> List[str]:
        return [rel.target_uuid for rel in self.get_relationships() if rel.type == rel_type]

    def has_relationship(self, rel_type: RelationshipType, target_uuid: Union[str, uuid.UUID]) -> bool:
        normalized = str(target_uuid)
        return any(rel.type == rel_type and rel.target_uuid == normalized for rel in self.get_relationships())

    def add_relationship(self, rel_type: RelationshipType, target_uuid: Optional[Union[str, uuid.UUID]]):
        if target_uuid is None:
            return
        normalized = str(target_uuid)
        relationships = self.get_relationships()
        if not any(rel.type == rel_type and rel.target_uuid == normalized for rel in relationships):
            relationships.append(Relationship(rel_type, normalized))

    def remove_relationship(self, rel_type: RelationshipType, target_uuid: Union[str, uuid.UUID]):
        normalized = str(target_uuid)
        relationships = self.get_relationships()
        relationships[:] = [rel for rel in relationships if not (rel.type == rel_type and rel.target_uuid == normalized)]

    def clear_relationships(self, rel_type: RelationshipType):
        relationships = self.get_relationships()
        relationships[:] = [rel for rel in relationships if rel.type != rel_type]

    def find_by_uuid(self, search_uuid: Union[str, uuid.UUID]) -> Optional['DatablockProxy']:
        normalized = str(search_uuid)
        if str(self.fn_uuid) == normalized:
            return self
        for child in self.children:
            found = child.find_by_uuid(normalized)
            if found:
                return found
        return None

    def clone(self) -> 'DatablockProxy':
        # logger.log(f"[DatablockProxy] Cloning: {self.path} (UUID: {self.fn_uuid})")
        cloned_node = DatablockProxy(
            path=self.path,
            fn_uuid=self.fn_uuid,
            properties=deepcopy(self.properties)
        )

        for child in self.children:
            cloned_child = child.clone()
            cloned_child.parent = cloned_node
            cloned_node.children.append(cloned_child)

        return cloned_node

    def find_child_by_path(self, search_path: str) -> Optional['DatablockProxy']:
        # logger.log(f"[DatablockProxy] find_child_by_path: Searching for '{search_path}' from '{self.path}'")
        if not isinstance(search_path, str):
            return None

        # For absolute paths, we need to find the root of the tree first.
        if search_path.startswith('/'):
            root = self.get_root()
            # If the search path starts with the root's path, we make it relative
            if search_path.startswith(root.path):
                search_path = search_path[len(root.path):].lstrip('/')
                if not search_path: # The path was just the root
                    return root
            else: # The search path is absolute but doesn't match our tree
                return None

        # Process the relative path parts
        parts = search_path.split('/')
        current_node = self
        for part in parts:
            if not part: 
                continue # Skip empty parts from double slashes

            if part == '..':
                current_node = current_node.parent
                if current_node is None:
                    return None  # Tried to go above the tree's root
                continue
            
            found_child = None
            for child in current_node.children:
                child_name = child.path.split('/')[-1]
                if child_name == part:
                    found_child = child
                    break
            
            if found_child:
                current_node = found_child
            else:
                return None  # Path part not found
        
        return current_node

    def get_root(self) -> 'DatablockProxy':
        """Traverses up the tree to find the root proxy (the one with no parent)."""
        node = self
        while node.parent:
            node = node.parent
        return node

    def _recursive_merge(self, other_node: 'DatablockProxy', self_root: 'DatablockProxy', other_root: 'DatablockProxy'):
        for other_child in other_node.children:
            child_name = other_child.path.split('/')[-1]
            my_child_equivalent = self.find_child_by_path(child_name)

            if my_child_equivalent:
                my_child_equivalent.properties.update(deepcopy(other_child.properties))
                my_child_equivalent._recursive_merge(other_child, self_root, other_root)
            else:
                new_branch = other_child.clone()
                new_branch.parent = self
                new_branch.repath(other_root.path, self_root.path)
                self.children.append(new_branch)

                # Ensure newly merged objects/collections are linked to the target scene's root collection
                if new_branch.properties.get('datablock_type') in ['OBJECT', 'COLLECTION']:
                    new_branch.add_relationship(RelationshipType.COLLECTION_LINK, self_root.fn_uuid)

    def merge(self, other_root: 'DatablockProxy'):
        if not other_root:
            return
        
        # `self` is the root of the base scene.
        # First, merge the properties of the root proxy itself.
        self.properties.update(deepcopy(other_root.properties))

        # Then, start the recursive merge for the children.
        self._recursive_merge(other_root, self, other_root)

    def __repr__(self) -> str:
        return f"<DatablockProxy(path='{self.path}', children={len(self.children)})>"

    def get_tree_representation(self, level: int = 0) -> List[Dict[str, Any]]:
        """Returns a list of dictionaries representing the tree structure for UI display."""
        items = [{
            'name': self.path.split('/')[-1] or self.path, # Display name
            'path': self.path, # Full path for copying
            'indent_level': level
        }]
        for child in self.children:
            items.extend(child.get_tree_representation(level + 1))
        return items

    def repath(self, old_base_path: str, new_base_path: str):
        # 1. Repath the proxy itself
        if self.path.startswith(old_base_path):
            self.path = self.path.replace(old_base_path, new_base_path, 1)

        # 2. Recurse for all children
        for child in self.children:
            child.repath(old_base_path, new_base_path)

    def get_flat_list(self) -> List['DatablockProxy']:
        """Returns a flat list of all proxies in the subtree, including self."""
        flat_list = [self]
        for child in self.children:
            flat_list.extend(child.get_flat_list())
        return flat_list

    def is_ancestor(self, potential_ancestor: 'DatablockProxy') -> bool:
        """Checks if the given proxy is an ancestor of this proxy."""
        p = self.parent
        while p:
            if p == potential_ancestor:
                return True
            p = p.parent
        return False

    def _transfer_dependencies(self, source_root: 'DatablockProxy', target_root: 'DatablockProxy'):
        """
        Finds dependencies (like mesh data) for this proxy and its children,
        and ensures they exist in the target scene, cloning them if necessary.
        """
        for proxy in self.get_flat_list():
            data_relationships = proxy.get_relationships_by_type(RelationshipType.OBJECT_DATA)
            if not data_relationships:
                continue

            data_rel = data_relationships[0]
            original_data_proxy = source_root.find_by_uuid(data_rel.target_uuid)
            if not original_data_proxy:
                continue

            if target_root.find_by_uuid(data_rel.target_uuid):
                continue

            cloned_data_proxy = original_data_proxy.clone()
            cloned_data_proxy.repath(source_root.path, target_root.path)

            data_db_type = cloned_data_proxy.properties.get('datablock_type', '')
            namespace_name = constants.get_namespace_for_type(data_db_type)
            if not namespace_name:
                continue

            namespace_path = f"{target_root.path}/{namespace_name}"
            namespace_proxy = target_root.find_child_by_path(namespace_path)
            if not namespace_proxy:
                namespace_proxy = DatablockProxy(path=namespace_path, parent=target_root)

            cloned_data_proxy.parent = namespace_proxy
            namespace_proxy.children.append(cloned_data_proxy)
            cloned_data_proxy.path = f"{namespace_proxy.path}/{cloned_data_proxy.path.split('/')[-1]}"

    def reparent(self, new_parent_proxy: 'DatablockProxy') -> 'DatablockProxy':
        """
        Moves this proxy subtree to a new parent within a (potentially different) scene.
        """
        source_root = self.get_root()
        target_root = new_parent_proxy.get_root()

        self._transfer_dependencies(source_root, target_root)

        cloned_self = self.clone()
        cloned_self.repath(source_root.path, target_root.path)

        cloned_self.parent = new_parent_proxy
        new_parent_proxy.children.append(cloned_self)
        cloned_self.path = f"{new_parent_proxy.path}/{cloned_self.path.split('/')[-1]}"

        subtree_nodes = cloned_self.get_flat_list()
        subtree_uuid_set = {str(node.fn_uuid) for node in subtree_nodes}

        for p in subtree_nodes:
            if p.properties.get('datablock_type') in ['OBJECT', 'COLLECTION']:
                relationships = p.get_relationships()
                relationships[:] = [
                    rel for rel in relationships
                    if not (rel.type == RelationshipType.COLLECTION_LINK and rel.target_uuid not in subtree_uuid_set)
                ]
                p.add_relationship(RelationshipType.COLLECTION_LINK, target_root.fn_uuid)

        return cloned_self

    def _prune_if_orphan(self, scene_root: 'DatablockProxy'):
        """Private helper to check if a proxy is an orphan and prune it if so."""
        if self.properties.get('datablock_type') == 'OBJECT': return

        user_count = 0
        self_uuid = str(self.fn_uuid)
        for proxy in scene_root.get_flat_list():
            data_relationships = proxy.get_relationships_by_type(RelationshipType.OBJECT_DATA)
            if any(rel.target_uuid == self_uuid for rel in data_relationships):
                user_count += 1

        if user_count == 0:
            self.prune()

    def prune(self):
        """
        Removes this proxy from its parent and triggers a dependency check.
        """
        if not self.parent: return

        scene_root = self.get_root()

        dependencies = []
        for rel in self.get_relationships_by_type(RelationshipType.OBJECT_DATA):
            dep_proxy = scene_root.find_by_uuid(rel.target_uuid)
            if dep_proxy:
                dependencies.append(dep_proxy)

        try:
            self.parent.children.remove(self)
            self.parent = None
        except ValueError:
            return

        for dep in dependencies:
            dep._prune_if_orphan(scene_root)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the proxy and its entire hierarchy to a dictionary."""
        properties_copy = deepcopy(self.properties)
        relationships = properties_copy.get('_fn_relationships')
        if isinstance(relationships, list):
            serialized: List[Dict[str, Any]] = []
            for rel in relationships:
                if isinstance(rel, Relationship):
                    serialized.append(rel.to_dict())
                elif isinstance(rel, dict):
                    serialized.append(rel)
            properties_copy['_fn_relationships'] = serialized
        return {
            'path': self.path,
            'fn_uuid': str(self.fn_uuid),
            'properties': properties_copy,
            'children': [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], parent: Optional['DatablockProxy'] = None) -> 'DatablockProxy':
        """Deserializes a dictionary into a DatablockProxy object and its hierarchy."""
        properties = deepcopy(data.get('properties', {}))
        relationships = properties.get('_fn_relationships')
        if isinstance(relationships, list):
            converted: List[Relationship] = []
            for entry in relationships:
                if isinstance(entry, Relationship):
                    converted.append(entry)
                elif isinstance(entry, dict):
                    rel = Relationship.from_dict(entry)
                    if rel:
                        converted.append(rel)
            properties['_fn_relationships'] = converted
        proxy = cls(
            path=data['path'],
            fn_uuid=uuid.UUID(data['fn_uuid']), # Ensure we create a proper UUID object
            properties=properties,
            parent=parent
        )
        for child_data in data.get('children', []):
            cls.from_dict(child_data, parent=proxy)
        return proxy

