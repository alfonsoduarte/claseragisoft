# Clase RAG — n8n + pgvector

Material de la clase de RAG: **dos workflows de n8n** que juntos forman un sistema de
preguntas y respuestas sobre documentos PDF.

| Workflow | Qué hace |
| --- | --- |
| `01 - Ingesta de PDF a pgvector` | Recibe un PDF por formulario, le extrae el texto, lo corta en fragmentos, los convierte en vectores y los guarda en Postgres |
| `02 - Consulta RAG fundada` | Un agente que responde preguntas usando **sólo** los fragmentos recuperados de esa base, y cita de qué archivo salió |

Son dos workflows y no uno a propósito: la ingesta y la consulta corren en momentos
distintos, con ritmos distintos. Eso obliga a tener un almacén compartido y durable, que es
lo que aporta pgvector.

---

## Requisitos

- **Docker** y **Docker Compose**.
- Una cuenta y una API key del proveedor de embeddings.
- Una cuenta y una API key del proveedor del modelo de chat.

No hace falta instalar n8n ni Postgres en la máquina: van en contenedores.

---

## Puesta en marcha

```bash
git clone https://github.com/alfonsoduarte/claseragisoft.git
cd claseragisoft/clase-rag/docker

cp env.example .env
echo "N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)" >> .env

docker compose up -d
```

El editor queda en **http://localhost:5679**.

La primera vez te va a pedir crear la cuenta de dueño. Es local, poné lo que quieras.

Comprobación rápida de que la base vectorial quedó bien:

```bash
docker exec clase-rag-vectorstore psql -U raguser -d ragdb \
  -tAc "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

Tiene que responder `0.8.7` o superior.

---

## Credenciales

Son **tres credenciales** en n8n, y después hay que **asignarlas en 5 nodos** (ver más abajo).
Crearlas no alcanza.

En el editor: barra lateral → **Credentials** → **Add credential**.

### 1. Postgres — la base vectorial

Buscá el tipo **Postgres**. Poné como nombre `Postgres - base vectorial`.

| Campo en n8n | Valor |
| --- | --- |
| Host | `vectorstore` |
| Database | `ragdb` |
| User | `raguser` |
| Password | `ragpass` |
| Port | `5432` |
| SSL | `disable` (ya viene así, no lo toques) |
| SSH Tunnel | apagado |
| Maximum Number of Connections | `100` (dejalo) |

> ⚠️ **El host es `vectorstore`, no `localhost`.**
> Nada de `127.0.0.1` tampoco. Dentro del contenedor de n8n, `localhost` es n8n mismo.
> Como los contenedores comparten una red de Docker, se alcanzan por el **nombre del
> servicio**, que es el hostname. Este es el error número uno de esta clase.

### 2. OpenAI — los embeddings

Buscá el tipo **OpenAI**. Poné como nombre `OpenAI - embeddings`.

| Campo en n8n | Valor |
| --- | --- |
| API Key | tu clave, empieza con `sk-…` |
| Organization ID | vacío |
| Base URL | `https://api.openai.com/v1` (dejalo) |
| Add Custom Header | apagado |

El modelo que usan los nodos es `text-embedding-3-small`, que devuelve vectores de
**1536 dimensiones**.

### 3. DeepSeek — el modelo de chat

Buscá el tipo **DeepSeek**. Poné como nombre `DeepSeek - chat`.

| Campo en n8n | Valor |
| --- | --- |
| API Key | tu clave |

**Un solo campo.** La URL base está fija dentro del nodo; no hay campo para cambiarla.

### Alternativa gratuita: Google Gemini

Si no querés pagar nada, Gemini cubre **las dos mitades** con una sola cuenta y **sin
tarjeta**. Los nodos de n8n existen para ambos usos, pero hay que cambiar el proveedor en
los tres nodos de IA (ver *Cambiar de proveedor* más abajo).

Datos de la credencial — buscá el tipo **Google Gemini(PaLM) Api**:

| Campo en n8n | Valor |
| --- | --- |
| Host | `https://generativelanguage.googleapis.com` (ya viene) |
| API Key | la clave de https://aistudio.google.com/apikey |

La clave se saca en **Google AI Studio**, no en la consola de Google Cloud. Con aceptar los
términos, AI Studio te crea solo el proyecto y la clave. No hay que poner tarjeta.

> ⚠️ **Si ya tenés cuenta de Google Cloud**, AI Studio **no** te crea un proyecto
> automático: tenés que importar uno. Y si te falta permiso de IAM, el botón
> **Create API key** aparece deshabilitado con el mensaje *"You do not have permission to
> create a key in this project"*. La salida es crear un proyecto nuevo que **no** esté
> asociado a una organización.
> ⚠️ **No confundas AI Studio con Vertex AI.** AI Studio usa
> `generativelanguage.googleapis.com` y es gratis. Vertex AI usa `aiplatform.googleapis.com`
> y requiere facturación. Si un tutorial te manda a la consola de Cloud y a facturación, es
> el camino equivocado.

### Dónde va cada credencial

Crearlas no alcanza: **hay que asignarlas en cada nodo**, desde el desplegable
*Credential*. Estos son los 5 lugares:

| Workflow | Nodo | Credencial |
| --- | --- | --- |
| `01 - Ingesta` | `Guardar en pgvector` | Postgres |
| `01 - Ingesta` | `Embeddings OpenAI` | OpenAI |
| `02 - Consulta` | `base_conocimiento` | Postgres |
| `02 - Consulta` | `Embeddings OpenAI` | OpenAI |
| `02 - Consulta` | `Modelo DeepSeek` | DeepSeek |

> ⚠️ `Embeddings OpenAI` aparece en **los dos workflows** y son **dos nodos distintos**.
> Asignarla en uno no la asigna en el otro.

Los JSON vienen con un marcador `REEMPLAZAR` en el bloque de credencial **a propósito**:
así n8n te avisa que falta asignarla, en lugar de fallar en silencio en la primera corrida.

---

## Cambiar de proveedor

Si vas por la vía gratuita de Gemini, hay que cambiar tres nodos y volver a indexar:

| Workflow | Nodo | De | A |
| --- | --- | --- | --- |
| `01 - Ingesta` | `Embeddings OpenAI` | Embeddings OpenAI | **Embeddings Google Gemini** |
| `02 - Consulta` | `Embeddings OpenAI` | Embeddings OpenAI | **Embeddings Google Gemini** |
| `02 - Consulta` | `Modelo DeepSeek` | DeepSeek Chat Model | **Google Gemini Chat Model** |

> ⚠️ **Al cambiar el modelo de embeddings hay que reindexar todo.** Los vectores que ya
> están guardados se generaron con otra función, y las distancias contra los nuevos no
> significan nada. El sistema **no da error**: devuelve resultados que parecen razonables.
> Para reindexar: `TRUNCATE n8n_vectors;` y volver a subir los PDFs.

---

## Importar los workflows

En el editor: **Workflows** → **Add workflow** → menú **⋯** → **Import from file**.

| Archivo | Nombre esperado |
| --- | --- |
| `workflows/01-ingesta-pdf.json` | `01 - Ingesta de PDF a pgvector` |
| `workflows/02-consulta-rag.json` | `02 - Consulta RAG fundada` |

Después de importar, asigná las credenciales de la tabla de arriba y guardá con **Cmd+S**.

---

## Verificar que funcionó

**1. Activá el workflow 01** y abrí el formulario:

```text
http://localhost:5679/form/ingesta-pdf
```

Subí `dataset/01-manual-operaciones.pdf` con origen *Manual de operaciones*.

**2. Mirá lo que quedó guardado:**

```bash
docker exec -it clase-rag-vectorstore psql -U raguser -d ragdb
```

```sql
SELECT count(*) FROM n8n_vectors;

SELECT metadata->>'archivo' AS archivo, left(text, 70) AS fragmento
FROM n8n_vectors ORDER BY id;

-- 1536 números: eso es un embedding
SELECT left(embedding::text, 80) || ' ...' FROM n8n_vectors LIMIT 1;
SELECT vector_dims(embedding) FROM n8n_vectors LIMIT 1;
```

Con el manual de 2 páginas y `chunkSize: 1000` tienen que aparecer **3 fragmentos**.

**3. Activá el workflow 02** y preguntá en el chat:

- *"¿Cuánto dura la garantía estándar?"* → tiene que responder **18 meses** y decir de qué
  archivo salió.
- *"¿Cuánto sale el envío internacional?"* → tiene que **negarse**. Ese dato no está en
  ningún documento.

---

## Errores frecuentes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `getaddrinfo EAI_AGAIN vectorstore` | El host de la credencial Postgres quedó en `localhost` | Cambialo a `vectorstore` |
| El nodo dice "no credentials" | Creaste la credencial pero no la asignaste | Elegila del desplegable en el nodo |
| El formulario da 404 | El workflow no está activo | Prendé el toggle **Active** |
| El chat responde cualquier cosa | El modelo de embeddings del 02 no es el mismo que indexó | Revisá que los dos workflows usen el mismo, y reindexá |
| No encuentra un dato que **sí** está en el PDF | El PDF es un escaneo, sin capa de texto | Ver `dataset/03-acta-escaneada.pdf`: se indexa con **0 caracteres** y no da error |
| `different vector dimensions` | Ingesta y consulta usan modelos de distinta dimensión | Unificá el modelo y reindexá |

---

## Resetear

```sql
TRUNCATE n8n_vectors;
```

Y volver a subir los PDFs. Nada más: los workflows y las credenciales quedan intactos.

**Borrado total** (destruye credenciales y workflows):

```bash
cd clase-rag/docker
docker compose down -v
docker compose up -d
```

> La `N8N_ENCRYPTION_KEY` del `.env` cifra las credenciales guardadas. Si la perdés o la
> cambiás, las credenciales dejan de poder descifrarse aunque los volúmenes sigan ahí.

---

## Estructura del repositorio

```text
clase-rag/
├── docker/
│   ├── docker-compose.yml              # n8n + pgvector desde cero
│   ├── docker-compose.vectorstore.yml  # agrega pgvector a un n8n que ya existe
│   └── env.example                     # copiar a .env
├── db/
│   └── init.sql                        # extensión vector + DDL documentado
├── workflows/
│   ├── 01-ingesta-pdf.json
│   └── 02-consulta-rag.json
├── dataset/
│   ├── generar-dataset.py              # regenera el corpus de prueba
│   ├── 01-manual-operaciones.pdf       # texto normal
│   ├── 02-tarifario-servicios.pdf      # con tabla de precios
│   └── 03-acta-escaneada.pdf           # SIN capa de texto (caso de estudio)
└── docs/
    └── guion-docente.md                # guion de la clase, bloque por bloque

odd/tasks/rag-clase.md                  # planificación y evidencia
```

## Documentación

- **`docs/guion-docente.md`** — el guion completo de la clase: qué decir en cada bloque, la
  secuencia de demos, los errores que conviene dejar que ocurran y la tarea para los alumnos.

## Puertos

| Servicio | Puerto en tu máquina |
| --- | --- |
| Editor de n8n | `5679` |
| Postgres de la base vectorial | `5433` |
| Postgres interno de n8n | no expuesto |

Se usan `5679` y `5433` para no chocar con un n8n o un Postgres que ya tengas corriendo en
`5678` y `5432`.
