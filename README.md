# Datablock Nodes: A Procedural Scene Engine for Blender

**Architecture Version: 18.0 ("The Audit")**

---

### 1. Vision: Your Scene as a Computable Data Stream

**Datablock Nodes** transforms Blender into a fully procedural, non-destructive scene composition tool, inspired by industry standards like Gaffer and USD.

Instead of manually managing objects, collections, and properties, you define your entire scene using a node tree. This tree is a "recipe" that the engine uses to construct the scene. The core principle is **Idempotency**: executing the same node tree always produces the exact same result.

Crucially, the engine intelligently preserves your manual tweaks. If you move an object created by the nodes, that change is saved as a **user override** and automatically reapplied on the next execution.

---

### 2. Core Concepts for Users

#### a. The Proxy Graph
What flows between the nodes is not actual Blender data, but **Datablock Proxies**. A proxy is a lightweight blueprint—an *intent* to create an object, a material, or a collection with specific properties and relationships. The entire node tree generates a final graph of these proxies.

#### b. The Execution Flow
When you activate an output node, the engine does the following:
1.  **Evaluates** the node tree to get the final proxy graph.
2.  **Plans** the safest and most efficient creation order.
3.  **Materializes** the proxies into actual Blender datablocks (objects, collections, etc.).
4.  **Applies** all properties and relationships (parenting, collection membership) defined in the nodes.
5.  **Re-applies** any persistent user overrides you have made.

#### c. The Override System
This is the key to a non-destructive workflow.
- **Automatic Detection:** Any change you make to a managed datablock (e.g., moving an object, changing a color) is automatically detected.
- **Persistent Storage:** The change is stored as an "override" linked to that specific datablock's unique ID.
- **Override Panel:** You have full control. In the Node Editor's side panel (`N` key), under "Datablock Nodes", you can see all active overrides and choose to clear them individually or all at once. This reverts the datablock to the state defined by the nodes.

---

### 3. Basic Workflow Example

1.  **Create a Scene:** Add a `Scene` node. This is the root of your proxy graph.
2.  **Create an Object:** Add a `Create Object` node (e.g., a Cube).
3.  **Create a Collection:** Add a `Collection` node named "MyCubes".
4.  **Put the Object in the Collection:** Use a `Set Collection` node. Wire the object and the collection into it.
5.  **Merge them:** Use a `Merge` node to combine the object/collection branch into your main scene branch.
6.  **Visualize:** Connect the `Merge` node to an `Outliner` node or activate its output socket to materialize the scene.
7.  **Override:** Go to the 3D View, move the cube that appeared. Notice the change persists. Go to the Node Editor's side panel, and you will see your modification listed as an override. Click "Clear All Overrides" to snap it back to the position defined by the nodes.
