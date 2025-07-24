from collections import deque
from .. import logger

def plan_execution(root_proxy):
    """
    Creates a dependency-resolved execution plan using a topological sort.
    Ensures that data-blocks (lights, meshes) are created before the objects that use them.
    """
    if not root_proxy:
        return []

    # 1. Flatten the tree into a list and a map for easy lookup
    all_proxies = root_proxy.get_flat_list()
    proxy_map = {p.path: p for p in all_proxies}

    # 2. Build the dependency graph and in-degree map
    adj = {p.path: [] for p in all_proxies}
    in_degree = {p.path: 0 for p in all_proxies}

    for proxy in all_proxies:
        # Hierarchy dependency: a child depends on its parent
        if proxy.parent:
            adj[proxy.parent.path].append(proxy.path)
            in_degree[proxy.path] += 1

        # Relationship dependencies
        if '_fn_relationships' in proxy.properties:
            for rel_type, target_value in proxy.properties['_fn_relationships'].items():
                # The target can be a single path (string) or a list of paths
                target_paths = target_value if isinstance(target_value, list) else [target_value]

                for target_path in target_paths:
                    if target_path in adj:
                        # The current proxy depends on the target of the relationship
                        adj[target_path].append(proxy.path)
                        in_degree[proxy.path] += 1

    # 3. Kahn's Algorithm for Topological Sort
    queue = deque([path for path, degree in in_degree.items() if degree == 0])
    sorted_plan = []

    while queue:
        path = queue.popleft()
        sorted_plan.append(proxy_map[path])

        for neighbor_path in adj[path]:
            in_degree[neighbor_path] -= 1
            if in_degree[neighbor_path] == 0:
                queue.append(neighbor_path)

    if len(sorted_plan) == len(all_proxies):
        logger.log(f"[Planner] Successfully created execution plan with {len(sorted_plan)} steps.")
        return sorted_plan
    else:
        # Cycle detected, this is an error in the graph structure
        logger.log(f"[Planner] CRITICAL ERROR: Cycle detected in dependency graph.")
        logger.log(f"[Planner] Plan length: {len(sorted_plan)}, Total prims: {len(all_proxies)}")
        # For now, return a partially sorted list to aid debugging
        return [] # Return an empty plan to prevent partial materialization
