# FNSelect: The Datablock Nodes Selection Language

**Version: 1.0**

## 1. Introduction

FNSelect is a powerful, human-readable language designed to select and filter proxies within the Datablock Nodes system. It combines the hierarchical path matching of Gaffer with the attribute filtering of CSS selectors, providing a fast and intuitive workflow.

A selection rule is a simple string that can be written directly into the "Selection" input sockets of most modifier nodes (`Set Property`, `Prune`, etc.), eliminating the need for extra `Select` nodes.

## 2. Core Concepts

A selection rule consists of two main parts: a **Path Pattern** and zero or more **Filter Blocks**.

`path_pattern[filter1][filter2]...`

--- 

## 3. Path Patterns

The path pattern determines which proxies are initially considered for selection based on their hierarchical path.

### Exact Path

The most basic selection. It matches a single proxy with the exact path specified.

- **Example**: `/root/objects/MyCube`

### Wildcards

Wildcards allow for flexible path matching.

-   `*` **(Asterisk)**: Matches any sequence of characters within a *single* path segment (it does not cross slashes `/`).
    -   `*light*`: Matches any proxy whose name contains "light".
    -   `/root/objects/light_*`: Matches proxies starting with "light_" directly inside `/root/objects`.

-   `...` **(Ellipsis)**: Matches any sequence of path segments, including zero or more levels of hierarchy. It is the most powerful wildcard for deep searches.
    -   `/.../controls`: Finds any proxy named "controls" anywhere in the scene.
    -   `/root/characters/.../hand_ik`: Finds `hand_ik` at any level below `/root/characters`.

--- 

## 4. Filter Blocks

Filter blocks refine the results from the path pattern. They are enclosed in square brackets `[]` and are chained together for an implicit **AND** logic (a proxy must pass all filters to be selected).

### 4.1. Attribute Filters

These filters check the properties of the proxies themselves.

-   **Syntax**: `[key operator value]`
-   **Operators**: ` = ` (equals), ` != ` (not equals), ` > ` (greater than), ` < ` (less than), ` >= `, ` <= `.

**Examples**:
-   Select all meshes: `*[type=MESH]`
-   Select all visible objects: `*[hide_viewport=false]`
-   Select objects above a certain height: `*[location.2 > 10.5]` (Note: `location.2` accesses the 3rd element of the location list, i.e., the Z coordinate).
-   Select by name (alternative to path pattern): `*[name = "Character_Rig"]`

### 4.2. Relational Filters

These powerful filters can query properties of *related* proxies.

#### Standard Relations (Dot Notation)

You can query a related proxy's properties using a `.` in the key.

-   **Syntax**: `[relation_name.property operator value]`

**Examples**:
-   Select all objects whose **data** is a `MESH`: `*[data.type=MESH]`
-   Select all objects whose **parent's name** starts with "GRP_": `*[parent.name=GRP_*]`

#### Collection Membership

A special filter `member_of` is used to query collection relationships.

-   `=` **(Direct Membership)**: Checks if a proxy is a direct member of the specified collection.
    -   `[member_of = /.../Lighting]`

-   `in` **(Hierarchical Membership)**: Checks if a proxy is in the specified collection *or any of its sub-collections*.
    -   `[member_of in /.../Assets]`

--- 

## 5. Logic

-   **AND**: Chaining multiple filters together creates an AND condition. A proxy must satisfy all filters.
    -   `/.../props[type=OBJECT][data.type=MESH]` (Finds all object-type proxies in a "props" hierarchy that have mesh data).

-   **OR**: A comma `,` is used to separate independent queries. The final result is the union of all queries.
    -   `*[type=LIGHT], *[type=CAMERA]` (Selects all lights OR all cameras).

--- 

## 6. Cookbook: Practical Examples

| Goal                                                               | Selection Rule                                        |
| ------------------------------------------------------------------ | ----------------------------------------------------- |
| Select all lights in the scene.                                    | `*[type=LIGHT]`                                       |
| Select all objects whose name ends with `_high`.                   | `*[name=*_high]`                                      |
| Select all objects that are children of `Character_Rig`.           | `*[parent.name=Character_Rig]`                        |
| Select all objects whose data is a `LIGHT`.                        | `*[data.type=LIGHT]`                                  |
| Select all meshes inside the `Vehicles` collection hierarchy.      | `*[type=MESH][member_of in /.../Vehicles]`           |
| Select all cameras and all lights.                                 | `*[type=CAMERA], *[type=LIGHT]`                       |
| Select all objects with more than 1000 polygons (hypothetical).    | `*[data.poly_count > 1000]`                           |
| Select all objects except those named "Floor".                     | `*[name != Floor]`                                    |

