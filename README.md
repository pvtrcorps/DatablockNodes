# Datablock Nodes: Un Motor de Composición de Escenas para Blender

**Versión de Arquitectura: 8.0 ("El Estándar de la Industria")**

---

### 1. Visión y Filosofía: Hacia Dónde Vamos

**Datablock Nodes** es un motor de composición de escenas para Blender, diseñado bajo una filosofía procedural y no destructiva. Nuestra visión es alinear Blender con los flujos de trabajo estándar de la industria, inspirándonos directamente en los principios de **Gaffer** y la estructura de datos de **Universal Scene Description (USD)** de Pixar.

**Queremos ser la capa de abstracción que le da superpoderes a Blender.** No reemplazamos el sistema de datos de Blender, sino que lo envolvemos en un paradigma nodal más potente, donde la escena se trata como un flujo de datos computable.

Nuestra dirección de diseño se basa en tres pilares:

1.  **Estructura de Datos (Inspirada en USD):** La unidad fundamental es el `DatablockProxy` (nuestro `Prim`), identificado por un `path` jerárquico. La jerarquía de `paths` define tanto la **organización** como la **jerarquía de transformación**, unificando ambos conceptos como lo hace USD.
2.  **Funcionamiento Nodal (Inspirado en Gaffer):** La escena fluye de nodo en nodo. Nodos atómicos y predecibles (`Parent`, `Merge`, `SetProperty`) se combinan para crear operaciones complejas. La lógica es explícita y visible en el grafo.
3.  **Experiencia de Usuario (Nativa de Blender):** El resultado final de nuestro grafo de proxies se "materializa" en datablocks y relaciones nativas de Blender. El objetivo es que un artista de Blender, sin conocimientos previos de USD o Gaffer, pueda usar el addon de forma intuitiva.

---

### 2. Arquitectura del Núcleo y Flujo de Datos

El sistema se fundamenta en varios conceptos clave que definen cómo viaja y se transforma la información.

#### a. El `DatablockProxy`: La Primitiva de la Escena

La estructura de datos fundamental que fluye por los nodos no es un objeto de Blender, sino un objeto Python llamado `DatablockProxy` (definido en `proxy_types.py`). Este objeto es un "plano" o una "intención" de que algo exista.

- **Atributos Clave:**
    - **`path`:** Una ruta jerárquica única (ej. `/root/character/rig/controls`) que define la posición del prim en el grafo de la escena. **Este path representa directamente la jerarquía de transformación.**
    - `fn_uuid`: Un identificador universal único y persistente. Es crucial para la estabilidad de los overrides manuales.
    - `properties`: Un diccionario que contiene todos los atributos del prim (su `datablock_type`, `name`, etc.) y sus relaciones (`_fn_relationships`).
    - `parent` y `children`: Definen la estructura del árbol de proxies.

#### b. Jerarquía `Object/Data`

Para representar un objeto de Blender, usamos una jerarquía de proxies anidada y estricta. Un objeto `Light` llamado `KeyLight` se representa como:
- Un proxy de tipo `OBJECT` en el path `/root/KeyLight`.
- Un proxy de tipo `LIGHT` (el data) en el path `/root/KeyLight/data`.

Esta estructura es una convención fija que nos alinea con la forma en que USD separa la transformación de los datos.

#### c. El Flujo de "Escena Única" y la Clonación

Los nodos se conectan mediante un `FNSocketScene`. Este socket no transporta listas de objetos, sino **una única referencia al `DatablockProxy` raíz** de un árbol de escena.

El flujo es estrictamente **no destructivo**. Cada nodo que modifica una escena sigue este patrón:
1.  Recibe un `DatablockProxy` raíz como entrada.
2.  **Clona** profundamente todo el árbol de proxies entrante (`proxy.clone()`).
3.  Realiza sus modificaciones sobre la escena clonada.
4.  Devuelve el `DatablockProxy` raíz de la escena modificada en su socket de salida.

---

### 3. El Motor de Ejecución (Directorio `engine`)

El directorio `engine` es el cerebro del addon. Orquesta el proceso de convertir el grafo de nodos en una escena real de Blender.

#### a. Fase 1: Orquestación (`orchestrator.py`)

1.  **Evaluación del Grafo de Nodos:** El orquestador comienza en el nodo final activo y viaja "hacia atrás", ejecutando la lógica `execute()` de cada nodo para obtener el `DatablockProxy` raíz final.
2.  **Llamada al Planificador:** Este proxy raíz se pasa al planificador.
3.  **Sincronización y Destrucción:** Compara los `fn_uuid` del plan con los datablocks ya gestionados. Los que ya no están en el plan se destruyen.
4.  **Llamada al Materializador:** El plan de ejecución se pasa al materializador.

#### b. Fase 2: Planificación (`planner.py`)

- El planificador recibe el proxy raíz, aplana la jerarquía y construye un grafo de dependencias basado **únicamente en relaciones explícitas** (`_fn_relationships`). La jerarquía de `paths` no se usa para el orden de creación.
- Utiliza un **ordenamiento topológico** para producir una lista lineal de proxies en el orden correcto de creación: el **plan de ejecución**.

#### c. Fase 3: Materialización (`materializer.py`)

El materializador recibe el plan y lo convierte en datablocks reales en tres pasadas:

1.  **Pasada 1: Creación:** Crea los datablocks (`Object`, `Mesh`, `Light`...) y les asigna su `fn_uuid`.
2.  **Pasada 2: Configuración y Overrides:** Aplica las propiedades base del proxy y, crucialmente, las modificaciones manuales del artista.
3.  **Pasada 3: Relaciones:**
    - **Parentesco:** Infiere la jerarquía de transformación directamente de la estructura de `paths` de los proxies y la crea en Blender.
    - **Otras Relaciones:** Establece enlaces a colecciones y otras relaciones explícitas.

---

### 4. El Sistema de Overrides Manuales

Esta es una de las características más potentes.
1.  Cuando un objeto se materializa, su estado "puro" se guarda en un snapshot.
2.  El artista puede modificar libremente el objeto en el viewport.
3.  Un handler (`override_handler.py`) detecta el cambio, lo compara con el snapshot y guarda la diferencia ("delta").
4.  En la siguiente ejecución, el `materializer` aplica el estado de los nodos y, justo después, aplica este delta, asegurando que el trabajo manual siempre tenga la última palabra.

---

### 5. Sistema de Selección: El Nodo `Select`

El sistema de selección utiliza un lenguaje de consulta para identificar prims.

`patrón_de_ruta {filtro_1; filtro_2; ...}`

- **Patrón de Ruta:** Usa wildcards (`*` y `**`) para seleccionar por `path`.
- **Filtros:** Refinan la selección por propiedades (`name:lamp`, `type:MESH`).

**Ejemplos:**
- `/root/geo/props/*`
- `** {type:LIGHT}`
- `/root/geo/** {type:MESH}`

---

### 6. Tipos de Nodos Principales

- **Generators:** Crean escenas desde cero (`Light`, `Cube`, `Import`).
- **Selection:** Crean y manipulan consultas de selección (`Select`, `Union`).
- **Modifiers:** Modifican los proxies seleccionados (`Set Property`, `Prune`).
- **Hierarchy:** Modifican la estructura de la escena.
    - **`Parent`:** Establece la jerarquía de transformación, re-escribiendo el `path` de los hijos para anidarlos bajo el padre.
- **Composition:**
    - **`Merge`:** Compone dos escenas. Utiliza una lógica de **fusión profunda (deep merge)**. Si un prim existe en ambas entradas, sus propiedades se fusionan (la segunda entrada gana en caso de conflicto) y sus hijos se combinan.
- **Executors:** Realizan acciones en el mundo real (`Batch Render`).