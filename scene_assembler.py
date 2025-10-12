"""
Scene Assembler: The builder of the proxy hierarchy.

This module provides a high-level API to build a valid and coherent
DatablockProxy tree. It centralizes all logic for creating namespaces (e.g., /objects),
assigning hierarchical paths, and managing relationships, ensuring that all
generator nodes and importers produce consistent scene structures.
"""


from . import state_manager
from .proxy_types import DatablockProxy, RelationshipType
from .engine import constants

class SceneAssembler:
    def __init__(self, scene_name: str, scene_uuid=None):
        """
        Initializes the assembler for a new scene.

        Args:
            scene_name: The name of the root scene to be built.
            scene_uuid: A persistent UUID for the scene's root proxy.
        """
        self.root_proxy = DatablockProxy(
            path=f"/{scene_name}",
            fn_uuid=scene_uuid, # Use the provided UUID
            properties=state_manager.define_new_state('SCENE', scene_name)
        )
        self._namespace_cache = {}

    def _get_or_create_namespace(self, namespace_name: str) -> DatablockProxy:
        """Creates or returns a virtual namespace proxy (with no datablock)."""
        if namespace_name in self._namespace_cache:
            return self._namespace_cache[namespace_name]
        
        namespace_path = f"{self.root_proxy.path}/{namespace_name}"
        namespace_proxy = DatablockProxy(path=namespace_path, parent=self.root_proxy)
        self._namespace_cache[namespace_name] = namespace_proxy
        return namespace_proxy

    def add_proxy(self, name: str, datablock_type: str, parent_proxy: DatablockProxy = None, fn_uuid=None) -> DatablockProxy:
        """
        The main method for adding a new proxy to the scene tree.
        It handles placing it in the correct namespace and defining its initial state.
        """
        # V17.2: Normalize the incoming datablock type to our internal canonical type.
        # This makes the assembler robust to receiving raw Blender types (e.g., 'SunLight').
        normalized_type = constants.BLENDER_TO_FN_TYPE.get(datablock_type, datablock_type)

        if parent_proxy:
            parent = parent_proxy
        else:
            # Use the NORMALIZED type to find the canonical namespace.
            namespace_name = constants.get_namespace_for_type(normalized_type)
            if not namespace_name:
                # Fallback to the root if the type has no defined namespace.
                parent = self.root_proxy
            else:
                parent = self._get_or_create_namespace(namespace_name)

        new_proxy = DatablockProxy(
            path=f"{parent.path}/{name}",
            fn_uuid=fn_uuid, # Use the provided UUID
            # Use the NORMALIZED type to create the initial state.
            properties=state_manager.define_new_state(normalized_type, name),
            parent=parent
        )
        return new_proxy

    def add_object_with_data(self, object_name: str, data_name: str, data_type: str, object_uuid=None, data_uuid=None) -> tuple[DatablockProxy, DatablockProxy]:
        """
        A convenience method for the common case of creating an object with its data.

        Args:
            object_name: The name of the object to create.
            data_name: The name of the data datablock (mesh, light, etc.).
            data_type: The type of the data datablock ("MESH", "LIGHT", etc.).
            object_uuid: A persistent UUID for the object proxy.
            data_uuid: A persistent UUID for the data proxy.

        Returns:
            A tuple containing (object_proxy, data_proxy).
        """
        data_proxy = self.add_proxy(data_name, data_type, fn_uuid=data_uuid)
        object_proxy = self.add_proxy(object_name, "OBJECT", fn_uuid=object_uuid)

        # Create the relationship between the object and its data.
        object_proxy.clear_relationships(RelationshipType.OBJECT_DATA)
        object_proxy.add_relationship(RelationshipType.OBJECT_DATA, data_proxy.fn_uuid)

        # V17.11: Explicitly link the new object to the scene collection by default.
        self.link_to_scene_collection(object_proxy)

        return object_proxy, data_proxy

    def link_to_scene_collection(self, proxy_to_link: DatablockProxy):
        """
        Adds a relationship to ensure that a proxy (object or collection) is
        linked to the scene's master collection.
        """
        proxy_to_link.add_relationship(RelationshipType.COLLECTION_LINK, self.root_proxy.fn_uuid)

    def get_root_proxy(self) -> DatablockProxy:
        """Returns the root proxy of the constructed scene tree."""
        return self.root_proxy