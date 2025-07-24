# Datablock Nodes: Un Motor de Composición de Escenas para Blender

**Versión de Arquitectura: 9.0 ("El Motor Optimizado")**

---

### 1. Visión y Filosofía: Hacia Dónde Vamos

**Datablock Nodes** es un motor de composición de escenas para Blender, diseñado bajo una filosofía procedural y no destructiva. Nuestra visión es alinear Blender con los flujos de trabajo estándar de la industria, inspirándonos directamente en los principios de **Gaffer** y la estructura de datos de **Universal Scene Description (USD)** de Pixar.

**Queremos ser la capa de abstracción que le da superpoderes a Blender.** No reemplazamos el sistema de datos de Blender, sino que lo envolvemos en un paradigma nodal más potente, donde la escena se trata como un flujo de datos computable.

Nuestra dirección de diseño se basa en tres pilares:

1.  **Estructura de Datos (Inspirada en USD):** La unidad fundamental es el `DatablockProxy` (nuestro `Prim`), identificado por un `path` jerárquico. La jerarquía de `paths` define **únicamente la jerarquía de transformación (parentesco)**.
2.  **Funcionamiento Nodal (Inspirado en Gaffer):** La escena fluye de nodo en nodo. Nodos atómicos y predecibles (`Parent`, `Merge`, `SetProperty`) se combinan para crear operaciones complejas. La lógica es explícita y visible en el grafo.
3.  **Experiencia de Usuario (Nativa de Blender):** El resultado final de nuestro grafo de proxies se "materializa" en datablocks y relaciones nativas de Blender. El objetivo es que un artista de Blender, sin conocimientos previos de USD o Gaffer, pueda usar el addon de forma intuitiva.

---

### 2. Arquitectura del Núcleo y Flujo de Datos

El sistema se fundamenta en varios conceptos clave que definen cómo viaja y se transforma la información.

#### a. El `DatablockProxy`: La Primitiva de la Escena

La estructura de datos fundamental que fluye por los nodos es un objeto Python llamado `DatablockProxy` (definido en `proxy_types.py`).

- **Atributos Clave:**
    - **`path`:** Una ruta jerárquica única (ej. `/root/character/rig`) que define la posición del prim en la jerarquía de transformación.
    - `fn_uuid`: Un identificador universal único y persistente, crucial para la estabilidad de los overrides manuales.
    - `properties`: Un diccionario que contiene todos los atributos del prim (su `datablock_type`, `name`, etc.) y sus relaciones (`_fn_relationships`).
    - `parent` y `children`: Definen la estructura del árbol de proxies.

#### b. Relación `Object/Data`

Para representar un objeto de Blender, creamos dos proxies **hermanos** (al mismo nivel jerárquico):
- Un proxy de tipo `OBJECT` (ej. en `/root/KeyLight`).
- Un proxy de tipo `LIGHT` (el data, ej. en `/root/KeyLight_data`).

La conexión entre ellos se establece mediante una relación explícita en las propiedades del `Object`: `_fn_relationships: {'data': '/root/KeyLight_data'}`. Este enfoque evita sobrecargar el `path` y mantiene una separación clara de conceptos.

#### c. El Flujo de "Escena Única" y la Clonación

Los nodos se conectan mediante un `FNSocketScene`. Este socket transporta una única referencia al `DatablockProxy` raíz de un árbol de escena. El flujo es **no destructivo**: cada nodo clona la escena entrante antes de modificarla.

---

### 3. El Motor de Ejecución Optimizado (Directorio `engine`)

El motor convierte el grafo de nodos en una escena real de Blender de forma eficiente.

#### a. Fase 1: Orquestación (`orchestrator.py`)

1.  **Evaluación del Grafo:** El orquestador comienza en el nodo final activo y viaja "hacia atrás", ejecutando la lógica `execute()` de cada nodo para obtener el `DatablockProxy` raíz final.
2.  **Sincronización y Destrucción:** Compara los `fn_uuid` del plan con los datablocks ya gestionados. Los que ya no están en el plan se destruyen de forma segura, actualizando el caché de UUIDs.

#### b. Fase 2: Planificación (`planner.py`)

- El planificador recibe el proxy raíz, aplana la jerarquía y construye un grafo de dependencias basado en la **jerarquía de `paths`** y en **relaciones explícitas** (`_fn_relationships`).
- Utiliza un **ordenamiento topológico** para producir una lista lineal de proxies en el orden correcto de creación: el **plan de ejecución**.

#### c. Fase 3: Materialización (`materializer.py`)

El materializador recibe el plan y lo convierte en datablocks reales en tres pasadas:

1.  **Pasada 1: Creación:** Crea los datablocks y les asigna su `fn_uuid`.
2.  **Pasada 2: Configuración y Overrides:** Aplica las propiedades base del proxy y las modificaciones manuales del artista. **Optimización:** Solo escribe una propiedad si su valor ha cambiado, minimizando las actualizaciones del `depsgraph`.
3.  **Pasada 3: Relaciones:** Establece el parentesco y otros enlaces entre los datablocks ya creados.

---

### 4. Sistemas de Rendimiento Clave

El addon incorpora varias optimizaciones críticas para asegurar una experiencia fluida.

#### a. El Caché de UUIDs (`uuid_manager.py`)

Para evitar escaneos completos y costosos de `bpy.data`, el `uuid_manager` mantiene un caché en memoria (`_UUID_CACHE`). Este mapa convierte las búsquedas de datablocks por UUID en operaciones de tiempo constante (O(1)), acelerando drásticamente el proceso de materialización.

#### b. El Sistema de Overrides Optimizado (`override_handler.py`)

Esta es una de las características más potentes y eficientes.
1.  Cuando un objeto se materializa, su estado "puro" se guarda en un snapshot.
2.  El artista puede modificar libremente el objeto en el viewport.
3.  **Optimización:** El handler escucha los `depsgraph.updates` de Blender. En lugar de comprobar todos los objetos, solo reacciona a los datablocks que han sido **efectivamente modificados** por el usuario.
4.  Para un objeto modificado, calcula la diferencia ("delta") con su snapshot y la guarda. Este delta se reaplica en futuras ejecuciones, asegurando que el trabajo manual siempre tenga la última palabra.

---

### 5. Tipos de Nodos Principales

- **Generators:** Crean escenas desde cero (`Light`, `Cube`).
- **Selection:** Crean y manipulan consultas de selección (`Select`).
- **Modifiers:** Modifican los proxies seleccionados (`Set Property`, `Prune`).
- **Hierarchy:**
    - **`Parent`:** Establece la jerarquía de transformación, re-escribiendo el `path` de los hijos para anidarlos bajo el padre.
- **Composition:**
    - **`Merge`:** Compone dos escenas. Utiliza una lógica de **fusión profunda (deep merge)**. Si un prim existe en ambas entradas, sus propiedades se fusionan (la segunda entrada gana) y sus hijos se combinan.
- **Executors:** Realizan acciones en el mundo real (`Batch Render`).
