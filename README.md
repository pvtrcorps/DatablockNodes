# Datablock Nodes Addon: Guía para Desarrolladores

Este documento describe la arquitectura y los principios fundamentales del addon Datablock Nodes para Blender. Su objetivo es proporcionar una comprensión clara del sistema para nuevos colaboradores, enfocándose en la gestión de datos, la idempotencia, el flujo de ejecución y la gestión de relaciones entre datablocks.

## 1. Objetivo Principal

El addon Datablock Nodes permite la manipulación programática y nodal de los datablocks de Blender (objetos, escenas, mallas, colecciones, etc.). El diseño busca ser **idempotente** (misma entrada siempre produce la misma salida) y permitir **ramificaciones explícitas** en el flujo de datos, similar a los Geometry Nodes de Blender. A diferencia de versiones anteriores, el sistema ahora opera bajo una **arquitectura de carga bajo demanda**. Esto significa que solo los datablocks de la rama activa del árbol de nodos existen en Blender en un momento dado. Los datablocks de ramas inactivas son destruidos para liberar recursos y se recrean cuando su rama se vuelve a activar, **preservando cualquier modificación manual realizada por el usuario**.

## 2. Principios Fundamentales

### 2.1. Arquitectura 100% Declarativa

El núcleo del addon es un paradigma estrictamente declarativo. Los nodos **nunca** modifican directamente el estado de Blender. En su lugar, **declaran** el estado final deseado, y un motor centralizado, el **Reconciliador**, se encarga de aplicar esos cambios de manera segura y eficiente.

### 2.2. Idempotencia y Preservación de Datos

*   **Idempotencia:** El sistema está diseñado para que, al ejecutar el árbol de nodos múltiples veces con las mismas entradas, el estado final de los datablocks en Blender sea siempre el mismo, sin crear duplicados (`.001`, `.002`, etc.).
*   **Preservación de Datos:** Un principio clave es permitir que las modificaciones manuales del usuario sobre un datablock (ej. mover un objeto, editar una malla) persistan entre activaciones de ramas. Cuando un datablock de una rama inactiva es destruido, sus propiedades modificadas manualmente son serializadas y almacenadas. Al recrearse el datablock (cuando su rama se activa de nuevo), estas modificaciones son restauradas. Esto se logra mediante:
    *   **UUIDs Persistentes:** Cada datablock gestionado por el addon recibe un UUID único (`_fn_uuid`) que se almacena directamente en el datablock de Blender.
    *   **Mapa de Overrides:** Una nueva estructura de datos persistente (`fn_override_map`) almacena las modificaciones manuales de los datablocks inactivos.

### 2.3. Ramificaciones Explícitas (Copy-on-Write)

El sistema no "adivina" cuándo debe copiar un datablock. La lógica es explícita y controlada por el `reconciler` y la mutabilidad de los sockets. Este mecanismo es crucial en la arquitectura de carga bajo demanda, ya que asegura que cada rama tenga su propia versión del datablock para modificar.

*   **Modificación In-Place:** Si un datablock se pasa a un nodo modificador y la salida del nodo anterior no tiene múltiples conexiones (no hay ramificación), el nodo modificador opera directamente sobre el datablock original.
*   **Copia-en-Escritura:** Si la salida de un nodo tiene múltiples conexiones (es un punto de ramificación) Y el socket de entrada del nodo siguiente es `is_mutable = True` (indicando que el nodo modificará el datablock), el `reconciler` crea una **copia implícita** del datablock. A esta copia se le asigna un **nuevo y único UUID** para asegurar que ambas ramas del flujo de datos puedan coexistir y ser gestionadas independientemente. Para nodos que explícitamente crean nuevas instancias (como 'Derive Datablock'), su socket de entrada debe tener `is_mutable = False` para evitar copias redundantes y asegurar que el nodo gestione su propia lógica de creación.

### 2.4. Gestión de Relaciones y Propiedades

Existen dos formas de declarar relaciones, dependiendo de la naturaleza de la operación:

*   **Asignación de Propiedades (Genérico):** Para la mayoría de las operaciones (asignar un material, un padre, un `world`), el nodo declara una **asignación de propiedad**. Esto le dice al reconciliador: "Asegúrate de que la propiedad `X` del datablock `A` apunte al datablock `B`". Este sistema es genérico y escalable.
*   **Relaciones de Colección (Específico):** Para operaciones que involucran colecciones de Blender (`.link`/`.unlink`), como añadir un objeto a una colección, el nodo declara una **relación de colección**. Esto es necesario porque estas operaciones no son simples asignaciones de propiedades.

## 3. Componentes Clave

### 3.1. `reconciler.py`

Es el motor de orquestación y el componente más crítico del addon. Su principio fundamental es que **el estado del archivo de Blender debe ser un reflejo del estado declarado por la rama activa del árbol de nodos**.

*   **`datablock_nodes_depsgraph_handler(scene, depsgraph)`**: El punto de entrada principal. Se dispara con cada actualización del `depsgraph` de Blender. Contiene un mecanismo de "cerrojo" para evitar re-entradas y bucles infinitos.
*   **`trigger_execution(tree)`**: Orquesta el proceso de evaluación y sincronización. Identifica la rama activa y delega la evaluación y la sincronización.
*   **`_evaluate_active_branch(tree, active_socket, active_branch_nodes)`**: Esta función evalúa **solo** los nodos que pertenecen a la rama activa, construyendo un "plan activo" en memoria (UUIDs, estados, relaciones, asignaciones de propiedades y declaraciones de creación/carga de archivos) para esa rama. Ahora también devuelve `load_file_declarations`.
*   **`_synchronize_blender_state(tree, active_uuids, active_states, active_relationships, active_assignments, creation_declarations)`**: El corazón del reconciliador en la nueva arquitectura. Su responsabilidad es asegurar que el estado de Blender coincida con el "plan activo".
    1.  **Fase de Destrucción:** Identifica todos los datablocks gestionados por el addon que **no** están en el `active_uuids` del plan. Para cada uno de ellos:
        *   Serializa sus propiedades modificadas manualmente usando `_serialize_overrides` y las guarda en el `fn_override_map`.
        *   Elimina el datablock de Blender (`bpy.data.collection.remove()`).
        *   Limpia sus entradas correspondientes de los mapas persistentes (`fn_state_map`, `fn_relationships_map`, `fn_property_assignments_map`).
    2.  **Fase de Creación/Actualización:** Para cada datablock en el `active_uuids` del plan, y siguiendo un orden topológico para respetar las dependencias:
        *   Si el datablock no existe en Blender (porque fue destruido o es nuevo), se crea (esto ocurre implícitamente a través de la ejecución de los nodos y las declaraciones `CREATE_DATABLOCK`, `DERIVE` o `COPY`).
        *   Inmediatamente después de la creación, llama a `_apply_overrides` para restaurar cualquier modificación manual previamente guardada.
        *   Aplica las propiedades y relaciones del plan activo de forma **defensiva** (solo si el valor en Blender difiere del plan), para evitar disparar el `depsgraph` innecesariamente.
*   **`_topological_sort_creation_declarations(creation_declarations)`**: Nueva función que ordena las declaraciones de creación para asegurar que los datablocks de origen se creen antes que los datablocks que dependen de ellos, resolviendo problemas de dependencias en cascada.
*   **`_serialize_overrides(datablock)`**: Nueva función que captura las propiedades modificadas manualmente de un datablock y las convierte a un string JSON. Maneja tipos complejos de Blender (`Vector`, `Matrix`, `bpy_prop_array`) convirtiéndolos a listas para la serialización.
*   **`_apply_overrides(datablock, tree)`**: Nueva función que lee el JSON de overrides y aplica las propiedades guardadas a un datablock. Reconstruye los tipos complejos de Blender a partir de las listas JSON.

### 3.2. Mapas de Estado en `DatablockTree`

*   **`fn_state_map`**: Registro de los datablocks creados o importados por los nodos.
*   **`fn_relationships_map`**: Registro de las relaciones de colección (`.link`/`.unlink`) declaradas.
*   **`fn_property_assignments_map`**: Registro de las asignaciones de propiedades genéricas declaradas.
*   **`fn_override_map`**: **Nuevo**. Almacena las propiedades modificadas manualmente de los datablocks que han sido destruidos (porque su rama se volvió inactiva), permitiendo su restauración al recrearse.

### 3.3. Nodos (ej. `nodes/new_datablock.py`, `nodes/set_object_parent.py`)

Los nodos operan bajo un un **principio estrictamente declarativo**. Su única responsabilidad es ejecutar su lógica interna y devolver un diccionario con sus resultados. **Nunca deben modificar el `NodeTree` (`tree`) ni el estado de Blender directamente.**

*   **Nodos Creadores/Modificadores:** Devuelven un diccionario que contiene el **UUID** del datablock de salida y, si aplica, una clave `'states'` para declarar la existencia de un datablock. Para declarar la creación de un nuevo datablock (como en `New Datablock` o `Derive Datablock`), se utiliza la clave `'declarations'` con el tipo de declaración (`'create_datablock'`, `'derive_datablock'`, `'copy_datablock'`).
*   **Nodos de Asignación de Propiedades (`set_object_parent`):** Devuelven una clave `'property_assignments'` con una lista de diccionarios que describen la asignación (`target_uuid`, `property_name`, `value_uuid` o `value_json`).
*   **Nodos de Relación de Colección (`link_to_collection`):** Devuelven una clave `'relationships'` con una lista de tuplas que describen el vínculo.
*   **Nodos Lectores de Propiedades (`get_datablock_content`):** Reciben UUIDs como entrada, utilizan `uuid_manager.find_datablock_by_uuid` para acceder a las propiedades del datablock en Blender, y devuelven **UUIDs** para cualquier datablock referenciado en sus salidas.

## 4. Flujo de Ejecución: Enfocado vs. Global

En la nueva arquitectura de carga bajo demanda, el sistema opera principalmente en un **Modo Enfocado**.

*   **Modo Enfocado (Principal):** Si un usuario activa un socket de salida (mediante el botón de activación en la UI del socket), el reconciliador evalúa **únicamente** la cadena de nodos que conduce a ese socket. Todos los datablocks que no forman parte de esta rama activa son destruidos, y solo los de la rama activa son creados/actualizados. Esto permite una gestión eficiente de los recursos y una visualización clara del resultado de una rama específica.
*   **Modo Global (Implícito/Transitorio):** El concepto de un "modo global" donde todos los datablocks existen simultáneamente ha sido eliminado. Si no hay ningún socket activo, el addon no realiza ninguna acción de sincronización, asumiendo que el usuario no ha declarado una rama activa para visualizar. La persistencia de los datablocks entre sesiones de Blender se gestiona a través de los overrides y la recreación bajo demanda.

## 5. Cómo Implementar un Nuevo Nodo

1.  **Crear un nuevo archivo Python** en la carpeta `nodes/`.
2.  **Definir la clase del nodo** heredando de `FNBaseNode` y `bpy.types.Node`.
3.  **Método `init(self, context)`:** Define los sockets de entrada y salida.
4.  **Método `execute(self, **kwargs)`:** Contiene la lógica principal del nodo. Este método es **estrictamente declarativo**.
    *   **NUNCA** modifique `kwargs.get('tree')` ni llame a `bpy.ops` o funciones que modifiquen el estado de Blender.
    *   **Si el nodo asigna una propiedad:** Devuelva una clave `'property_assignments'`.
        ```python
        return {
            self.outputs[0].identifier: my_object,
            'property_assignments': [{
                'target_uuid': uuid_of_my_object,
                'property_name': 'parent',
                'value_uuid': uuid_of_parent_object
            }]
        }
        ```
    *   **Si el nodo gestiona una relación de colección:** Devuelva una clave `'relationships'`.
        ```python
        return {
            self.outputs[0].identifier: output_collection,
            'relationships': [(obj_uuid, col_uuid, 'COLLECTION_OBJECT_LINK')]
        }
        ```
5.  **Registrar el nodo** en `__init__.py`.