# Datablock Nodes Addon: Guía para Desarrolladores

Este documento describe la arquitectura y los principios fundamentales del addon Datablock Nodes para Blender. Su objetivo es proporcionar una comprensión clara del sistema para nuevos colaboradores, enfocándose en la gestión de datos, la idempotencia, el flujo de ejecución y la gestión de relaciones entre datablocks.

## 1. Objetivo Principal

El addon Datablock Nodes permite la manipulación programática y nodal de los datablocks de Blender (objetos, escenas, mallas, colecciones, etc.). El diseño busca ser **idempotente** (misma entrada siempre produce la misma salida) y permitir **ramificaciones explícitas** en el flujo de datos, similar a los Geometry Nodes de Blender. El sistema está diseñado para gestionar datablocks de forma independiente de su linkado a la escena activa, permitiendo procesamiento "en segundo plano" y control granular sobre las relaciones.

## 2. Principios Fundamentales

### 2.1. Idempotencia y Preservación de Datos

*   **Idempotencia:** El sistema está diseñado para que, al ejecutar el árbol de nodos múltiples veces con las mismas entradas, el estado final de los datablocks en Blender sea siempre el mismo, sin crear duplicados (`.001`, `.002`, etc.).
*   **Preservación de Datos:** Un principio clave es permitir que las modificaciones manuales del usuario sobre un datablock (ej. mover un objeto, editar una malla) persistan entre ejecuciones del árbol de nodos, siempre y cuando ese datablock siga siendo gestionado por el árbol. Esto se logra mediante:
    *   **UUIDs Persistentes:** Cada datablock gestionado por el addon recibe un UUID único (`_fn_uuid`) que se almacena directamente en el datablock de Blender.

### 2.2. Ramificaciones Explícitas (Copy-on-Write)

El sistema no "adivina" cuándo debe copiar un datablock. La lógica es explícita y controlada por el `reconciler` y la mutabilidad de los sockets:

*   **Modificación In-Place:** Si un datablock se pasa a un nodo modificador y la salida del nodo anterior no tiene múltiples conexiones (no hay ramificación), el nodo modificador opera directamente sobre el datablock original.
*   **Copia-en-Escritura:** Si la salida de un nodo tiene múltiples conexiones (es un punto de ramificación) Y el socket de entrada del nodo siguiente es `is_mutable = True` (indicando que el nodo modificará el datablock), el `reconciler` crea una **copia** del datablock. A esta copia se le asigna un **nuevo y único UUID** para asegurar que ambas ramas del flujo de datos puedan coexistir y ser gestionadas independientemente.

### 2.3. Gestión Granular de Relaciones

El addon gestiona explícitamente las relaciones entre datablocks (ej. objetos linkados a colecciones, colecciones anidadas). Esto asegura que:
*   Las relaciones creadas por el addon se rastrean y se mantienen solo mientras sean "requeridas" por el árbol de nodos activo.
*   Las relaciones que ya no son necesarias se desvinculan automáticamente, manteniendo el archivo de Blender limpio y consistente con el estado del grafo.
*   El linkado de objetos y colecciones a la escena activa es una acción explícita del nodo `Link to Scene`, no un efecto secundario de la activación de un socket.

## 3. Componentes Clave

### 3.1. `reconciler.py`

Es el motor central del addon.
*   **`sync_active_socket(tree, active_socket)`:** Orquesta la ejecución del árbol de nodos, iniciando el proceso de evaluación y sincronización.
*   **`_evaluate_node_tree(tree, active_socket)`:** Realiza una evaluación "pull-style" desde el socket activo, construyendo el estado requerido de datablocks y relaciones.
*   **`_evaluate_node(tree, node, cache, evaluated_nodes_and_sockets)`:** Recursivamente evalúa un nodo y sus dependencias, utilizando un caché para evitar re-evaluaciones.
*   **`_diff_and_sync(tree, required_state, current_state, required_relationships)`:** La función más crítica para la gestión de datos y relaciones.
    *   Compara el estado `required_state` (datablocks y relaciones que deberían existir) con el `current_state` (lo que existe actualmente en Blender).
    *   Gestiona la persistencia (`use_fake_user`), visibilidad (renombrando con `.` prefijo) y eliminación de datablocks.
    *   **Gestiona relaciones:** Desvincula relaciones (ej. objeto de colección) que ya no están en `required_relationships`.
*   **`_get_managed_datablocks_in_scene()`:** Identifica todos los datablocks en el archivo de Blender que están siendo gestionados por el addon (tienen un `_fn_uuid`).

### 3.2. `uuid_manager.py`

Gestiona la asignación y búsqueda de UUIDs para los datablocks de Blender.
*   **`FN_UUID_PROPERTY = "_fn_uuid"`:** La clave utilizada para almacenar el UUID en el diccionario de propiedades del datablock.
*   **`get_uuid(datablock)`:** Recupera el UUID de un datablock.
*   **`set_uuid(datablock, target_uuid=None, force_new=False)`:** Asigna un UUID. Si `force_new=True`, siempre generará un nuevo UUID, incluso si el datablock ya tiene uno. Esto es vital para las copias en ramificaciones.
*   **`find_datablock_by_uuid(uuid_to_find)`:** Busca un datablock en las colecciones `bpy.data` (objetos, escenas, mallas, materiales, etc.) por su UUID.

### 3.3. `fn_state_map` (en `DatablockTree`)

Es una colección persistente (`bpy.props.CollectionProperty` de tipo `FNStateMapItem`) dentro del `NodeTree` que almacena los `node_id` y los `datablock_uuid` asociados. Actúa como un registro de los datablocks que el árbol de nodos está gestionando activamente. Es fundamental para la idempotencia y la recolección de basura.

### 3.4. `fn_relationships_map` (en `DatablockTree`)

Es una nueva colección persistente (`bpy.props.CollectionProperty` de tipo `FNRelationshipItem`) dentro del `NodeTree` que almacena las relaciones específicas entre datablocks creadas por los nodos del addon (ej. `source_uuid`, `target_uuid`, `relationship_type`). Es crucial para la gestión granular de relaciones y su desvinculación automática.

### 3.5. Nodos (ej. `nodes/new_datablock.py`, `nodes/link_to_collection.py`)

*   **Nodos Creadores (`FN_new_datablock`):** En su método `execute`, consultan el `fn_state_map` para ver si ya existe un datablock asociado a su `fn_node_id`. Si existe, lo actualizan; si no, crean uno nuevo y registran su UUID en el `fn_state_map`.
*   **Nodos Modificadores (`FN_set_datablock_name`):** Reciben el datablock (original o copia) preparado por el `reconciler` y realizan su operación. No necesitan implementar la lógica de ramificación directamente.
*   **Nodos de Relación (`FN_link_to_collection`):** Además de realizar la operación de linkado en Blender, registran la relación creada en `tree.fn_relationships_map` para que el `reconciler` pueda rastrearla y desvincularla si deja de ser requerida.

## 4. Flujo de Ejecución (Detallado)

1.  **Inicio:** `sync_active_socket` se llama, generalmente por un `depsgraph_update_post` handler.
2.  **Evaluación del Árbol (`_evaluate_node_tree`):**
    *   Se realiza una evaluación recursiva "pull-style" desde el socket activo hacia atrás a través de las conexiones.
    *   Cada nodo se ejecuta una vez, y sus resultados se almacenan en un caché de sesión.
    *   Durante la ejecución de nodos que crean relaciones (ej. `FN_link_to_collection`), estas relaciones se registran en `tree.fn_relationships_map`.
    *   Al finalizar, se obtiene el `required_state` (UUIDs de datablocks activos) y `required_relationships` (conjunto de tuplas `(source_uuid, target_uuid, relationship_type)` de las relaciones activas).
3.  **Recolección de Estado Actual (`_get_managed_datablocks_in_scene`):** Se identifican todos los datablocks actualmente gestionados por el addon en el archivo de Blender.
4.  **Sincronización y Recolección de Basura (`_diff_and_sync`):**
    *   **Datablocks:** Se comparan `required_state` con el estado actual. Los datablocks no requeridos pero con creador existente se ocultan (prefijo `.`) y se les asigna `use_fake_user = True`. Los datablocks huérfanos (sin nodo creador existente) se eliminan.
    *   **Relaciones:** Se comparan `required_relationships` con las relaciones almacenadas en `tree.fn_relationships_map`. Las relaciones que ya no son requeridas por el árbol activo se desvinculan de Blender (ej. `collection.objects.unlink(obj)`). Las entradas obsoletas en `tree.fn_relationships_map` y `tree.fn_state_map` se limpian.
5.  **Activación de Ruta:** Se marcan los sockets en la ruta activa con `is_active = True` para visualización.
6.  **Establecer Datablock Activo (si aplica):** Si el socket activo final es de tipo `Scene`, se establece como la escena activa de Blender.

## 5. Guías de Desarrollo y Estilo

*   **Convenciones:** Adherirse estrictamente a las convenciones de código existentes (formato, nombres, estructura).
*   **Blender API:** Utilizar la API de Blender de forma idiomática.
*   **Comentarios:** Añadir comentarios solo cuando sea necesario para explicar el *porqué* de una decisión compleja, no el *qué* hace el código.
*   **Pruebas:** Siempre que sea posible, crear pruebas unitarias o de integración para verificar el comportamiento de los nodos y el sistema.
*   **Consistencia de Relaciones:** Al definir nuevos tipos de relaciones, asegúrese de que sean claras y consistentes con los tipos existentes (ej. `COLLECTION_OBJECT_LINK`, `COLLECTION_CHILD_LINK`).
*   **Forma de los Sockets:** Utilice `socket.display_shape = 'SQUARE'` para los sockets que representan listas de datablocks (ej. `FNSocketObjectList`, `FNSocketCollectionList`). Esto proporciona una indicación visual clara de que el socket maneja múltiples elementos.

## 6. Cómo Implementar un Nuevo Nodo

Para implementar un nuevo nodo, siga estos pasos:

1.  **Crear un nuevo archivo Python** en la carpeta `nodes/` (ej. `my_new_node.py`).
2.  **Importar `bpy` y `FNBaseNode`:**
    ```python
    import bpy
    from ..nodes.base import FNBaseNode
    from .. import uuid_manager # Si necesita gestionar UUIDs
    ```
3.  **Definir la clase del nodo:** La clase debe heredar de `FNBaseNode` y `bpy.types.Node`.
    ```python
    class FN_my_new_node(FNBaseNode, bpy.types.Node):
        bl_idname = "FN_my_new_node"
        bl_label = "My New Node"
        # bl_icon = 'SOME_ICON' (opcional)
    ```
4.  **Método `init(self, context)`:** Define los sockets de entrada y salida del nodo.
    *   Use `self.inputs.new('FNSocketType', "Label")` y `self.outputs.new('FNSocketType', "Label")`.
    *   Configure `is_mutable = True` para sockets de entrada que el nodo modificará.
    ```python
    def init(self, context):
        FNBaseNode.init(self, context)
        self.inputs.new('FNSocketString', "Input String")
        self.outputs.new('FNSocketString', "Output String")
    ```
5.  **Método `update_hash(self, hasher)`:** Añade las propiedades del nodo que afectan su resultado al `hasher` para el sistema de caché.
    ```python
    def update_hash(self, hasher):
        # Ejemplo: si el nodo tiene una propiedad 'my_property'
        # hasher.update(str(self.my_property).encode())
        pass # Si no hay propiedades que afecten el resultado
    ```
6.  **Método `execute(self, **kwargs)`:** Contiene la lógica principal del nodo.
    *   Los valores de los sockets de entrada se pasan en `kwargs` (usando `socket.identifier` como clave).
    *   El objeto `tree` (el `NodeTree` principal) también se pasa en `kwargs['tree']`.
    *   **Gestión de UUIDs:** Si el nodo crea o modifica datablocks, use `uuid_manager.get_uuid()` y `uuid_manager.set_uuid()` para asegurar la idempotencia.
    *   **Registro de Relaciones:** Si el nodo crea relaciones entre datablocks (ej. `FN_link_to_collection`), registre estas relaciones en `tree.fn_relationships_map` usando `FNRelationshipItem`.
    *   Debe devolver un diccionario con los resultados de los sockets de salida.
    ```python
    def execute(self, **kwargs):
        input_string = kwargs.get(self.inputs['Input String'].identifier)
        # ... lógica del nodo ...
        output_string = input_string.upper() # Ejemplo
        return {self.outputs['Output String'].identifier: output_string}
    ```
7.  **Registrar el nodo:** En `__init__.py`, importe el nuevo archivo y añada la clase del nodo a la tupla `classes` y a `node_categories`.

## 7. Directrices de UI/UX (ToDo/NotToDo)

### ToDo (Lo que queremos lograr)

*   **Claridad Visual:** Los nodos deben ser visualmente claros y su propósito inmediatamente obvio.
*   **Minimalismo:** Evitar elementos de UI innecesarios en los nodos. La complejidad debe residir en el grafo, no en la interfaz de cada nodo.
*   **Consistencia:** Mantener un estilo visual y de interacción consistente en todos los nodos.
*   **Feedback Visual:** Proporcionar feedback visual claro sobre el estado de los nodos (ej. sockets activos, errores).
*   **Interactividad Intuitiva:** La manipulación de nodos y conexiones debe ser fluida y predecible.

### NotToDo (Lo que queremos evitar)

*   **Duplicación de Funcionalidad:** No replicar funcionalidades existentes de Blender si no aportan un valor nodal significativo.
*   **Interfaces Recargadas:** Evitar paneles de propiedades complejos dentro de los nodos que puedan ser mejor manejados por el sistema de propiedades de Blender o por nodos dedicados.
*   **Comportamiento Inesperado:** El sistema debe ser predecible. Las acciones del usuario o los cambios en el grafo no deben llevar a estados ambiguos o difíciles de depurar.
*   **Linkado Implícito:** **NO** linkar datablocks a la escena activa o a otras colecciones de forma automática o implícita. Esto debe ser siempre una acción explícita del usuario a través de nodos dedicados (ej. `Link to Scene`, `Link to Collection`).
*   **Dependencias Externas Innecesarias:** Minimizar las dependencias de librerías externas para mantener el addon ligero y compatible.

## 8. Depuración

Los `print` statements con prefijos como `[FN_new_object]`, `[UUID_MANAGER]`, `[RECONCILER]`, etc., son herramientas de depuración activas. Permiten seguir el flujo de ejecución, la gestión de UUIDs, las decisiones de ramificación y la reconciliación de relaciones en tiempo real. Son invaluables para entender y solucionar problemas en este sistema complejo.