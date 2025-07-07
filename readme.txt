# Datablock Nodes Addon: Guía para Desarrolladores

Este documento describe la arquitectura y los principios fundamentales del addon Datablock Nodes para Blender. Su objetivo es proporcionar una comprensión clara del sistema para nuevos colaboradores, enfocándose en la gestión de datos, la idempotencia y el flujo de ejecución.

## 1. Objetivo Principal

El addon Datablock Nodes permite la manipulación programática y nodal de los datablocks de Blender (objetos, escenas, mallas, etc.). El diseño busca ser **idempotente** (misma entrada siempre produce la misma salida) y permitir **ramificaciones explícitas** en el flujo de datos, similar a los Geometry Nodes de Blender.

## 2. Principios Fundamentales

### 2.1. Idempotencia y Preservación de Datos

*   **Idempotencia:** El sistema está diseñado para que, al ejecutar el árbol de nodos múltiples veces con las mismas entradas, el estado final de los datablocks en Blender sea siempre el mismo, sin crear duplicados (`.001`, `.002`, etc.).
*   **Preservación de Datos:** Un principio clave es permitir que las modificaciones manuales del usuario sobre un datablock (ej. mover un objeto, editar una malla) persistan entre ejecuciones del árbol de nodos, siempre y cuando ese datablock siga siendo gestionado por el árbol. Esto se logra mediante:
    *   **UUIDs Persistentes:** Cada datablock gestionado por el addon recibe un UUID único (`_fn_uuid`) que se almacena directamente en el datablock de Blender.
    

### 2.2. Ramificaciones Explícitas (Copy-on-Write)

El sistema no "adivina" cuándo debe copiar un datablock. La lógica es explícita y controlada por el `reconciler` y la mutabilidad de los sockets:

*   **Modificación In-Place:** Si un datablock se pasa a un nodo modificador y la salida del nodo anterior no tiene múltiples conexiones (no hay ramificación), el nodo modificador opera directamente sobre el datablock original.
*   **Copia-en-Escritura:** Si la salida de un nodo tiene múltiples conexiones (es un punto de ramificación) Y el socket de entrada del nodo siguiente es `is_mutable = True` (indicando que el nodo modificará el datablock), el `reconciler` crea una **copia** del datablock. A esta copia se le asigna un **nuevo y único UUID** para asegurar que ambas ramas del flujo de datos puedan coexistir y ser gestionadas independientemente.

## 3. Componentes Clave

### 3.1. `reconciler.py`

Es el motor central del addon.
*   **`execute_tree(tree)`:** Orquesta la ejecución del árbol de nodos.
*   **Ordenamiento Topológico (`_topological_sort`):** Determina el orden de ejecución de los nodos para resolver dependencias y detectar ciclos.
*   **`_prepare_node_inputs(node, tree, execution_cache)`:** La función más crítica para la gestión de datos. Aquí se implementa la lógica de ramificación:
    *   Verifica si un socket de salida tiene múltiples enlaces (`len(link.from_socket.links) > 1`).
    *   Verifica si el socket de entrada del nodo actual es mutable (`input_socket.is_mutable`).
    *   Si ambas condiciones se cumplen, se crea una copia del datablock.
    *   Gestiona la reutilización de copias existentes (si ya se creó una copia para esa rama en una ejecución anterior) o la creación de nuevas copias con `uuid_manager.set_uuid(..., force_new=True)`.
*   **`_garbage_collect(tree, managed_datablocks_before_execution)`:** Se encarga de eliminar los datablocks de Blender que ya no son gestionados por el árbol de nodos. Esto se logra comparando los UUIDs gestionados antes de la ejecución con los que permanecen activos. Además, limpia las entradas obsoletas en `fn_state_map` que ya no corresponden a nodos existentes en el árbol.

### 3.2. `uuid_manager.py`

Gestiona la asignación y búsqueda de UUIDs para los datablocks de Blender.
*   **`FN_UUID_PROPERTY = "_fn_uuid"`:** La clave utilizada para almacenar el UUID en el diccionario de propiedades del datablock.
*   **`get_uuid(datablock)`:** Recupera el UUID de un datablock.
    *   **`set_uuid(datablock, target_uuid=None, force_new=False)`:** Asigna un UUID. Si `force_new=True`, siempre generará un nuevo UUID, incluso si el datablock ya tiene uno. Esto es vital para las copias en ramificaciones.
*   **`find_datablock_by_uuid(uuid_to_find)`:** Busca un datablock en las colecciones `bpy.data` (objetos, escenas, mallas, materiales, etc.) por su UUID.

### 3.3. `fn_state_map` (en `DatablockTree`)

Es una colección persistente (`bpy.props.CollectionProperty`) dentro del `NodeTree` que almacena los `node_id` y los `datablock_uuid` asociados. Actúa como un registro de los datablocks que el árbol de nodos está gestionando activamente. Es fundamental para la idempotencia y la recolección de basura.

### 3.4. Nodos (ej. `nodes/new_object.py`, `nodes/new_scene.py`, `nodes/set_object_name.py`)

*   **Nodos Creadores (`FN_new_object`, `FN_new_scene`):** En su método `execute`, primero consultan el `fn_state_map` y usan `uuid_manager.find_datablock_by_uuid` para ver si ya existe un datablock asociado a su `fn_node_id`. Si existe, lo actualizan; si no, crean uno nuevo y registran su UUID en el `fn_state_map`.
*   **Nodos Modificadores (`FN_set_object_name`):** Reciben el datablock (original o copia) preparado por el `reconciler` y realizan su operación. No necesitan implementar la lógica de ramificación directamente, ya que el `reconciler` se encarga de pasarles la versión correcta del datablock.

## 4. Flujo de Ejecución (Simplificado)

1.  **Inicio:** `execute_tree` se llama.
2.  **Recolección de Estado Previo:** Se registran los UUIDs de los datablocks gestionados antes de la ejecución (`managed_datablocks_before_execution`).
3.  **Ordenamiento:** Los nodos se ordenan topológicamente.
4.  **Ejecución de Nodos (bucle):** Para cada nodo en el orden topológico:
    *   **Preparación de Entradas (`_prepare_node_inputs`):**
        *   Se recuperan los datablocks de la `execution_cache`.
        *   Se evalúa la lógica de ramificación (múltiples enlaces + socket mutable).
        *   Si hay ramificación, se crea una copia con un nuevo UUID (o se reutiliza una copia existente).
        *   El datablock (original o copia) se pasa al método `execute` del nodo.
    *   **Ejecución del Nodo (`node.execute`):** El nodo realiza su operación y devuelve el datablock resultante.
    *   **Almacenamiento en Caché:** El datablock resultante se guarda en la `execution_cache` para que los nodos posteriores puedan acceder a él.
5.  **Recolección de Basura (`_garbage_collect`):** Al finalizar la ejecución de todos los nodos, se comparan los datablocks gestionados al inicio con los gestionados al final. Los datablocks que ya no están en uso son eliminados de Blender.

## 5. Guías de Desarrollo y Estilo

*   **Convenciones:** Adherirse estrictamente a las convenciones de código existentes (formato, nombres, estructura).
*   **Blender API:** Utilizar la API de Blender de forma idiomática.
*   **Comentarios:** Añadir comentarios solo cuando sea necesario para explicar el *porqué* de una decisión compleja, no el *qué* hace el código.
*   **Pruebas:** Siempre que sea posible, crear pruebas unitarias o de integración para verificar el comportamiento de los nodos y el sistema.

## 6. Depuración

Los `print` statements con prefijos como `[FN_new_object]`, `[UUID_MANAGER]`, etc., son herramientas de depuración activas. Permiten seguir el flujo de ejecución, la gestión de UUIDs y las decisiones de ramificación en tiempo real. Son invaluables para entender y solucionar problemas en este sistema complejo.
