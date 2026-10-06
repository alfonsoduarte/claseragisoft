-- ===========================================================================
-- Base vectorial de la clase: se ejecuta UNA sola vez, cuando Docker crea el
-- volumen por primera vez.
--
-- Si modificás este archivo después, los cambios NO se aplican: el volumen ya
-- está inicializado. Para reindexar desde cero:
--     docker compose down -v && docker compose up -d
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1) La extensión que convierte Postgres en una base vectorial.
--    Sin esta línea no existen el tipo `vector` ni los operadores de distancia.
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- 2) La tabla de chunks.
--
--    NO la creamos aca a proposito. La crea el propio nodo "Postgres PGVector
--    Store" la primera vez que inserta, y lo hace con exactamente la forma que
--    el espera. Si la declaramos nosotros y no coincide, los inserts fallan
--    con errores dificiles de leer.
--
--    Esto es el DDL REAL que el nodo creo en la instancia de la clase,
--    obtenido con pg_dump despues de la primera ingesta:
--
--      CREATE TABLE public.n8n_vectors (
--        id        uuid DEFAULT gen_random_uuid() NOT NULL,
--        text      text,
--        metadata  jsonb,
--        embedding public.vector
--      );
--      ALTER TABLE ONLY public.n8n_vectors
--        ADD CONSTRAINT n8n_vectors_pkey PRIMARY KEY (id);
--
--    Tres cosas que conviene mirar de ese DDL:
--
--    a) `id` es uuid, no text, y el default lo pone POSTGRES (gen_random_uuid),
--       no el nodo. Cada ingesta inventa ids nuevos. Por eso subir dos veces el
--       mismo PDF duplica los fragmentos en lugar de reemplazarlos: ese es el
--       ejercicio de idempotencia de la clase.
--
--    b) `embedding public.vector` va SIN dimension. No dice vector(1536).
--       Comprobado: la columna acepta un vector de 3 dimensiones sin quejarse.
--       O sea que la base NO te protege de indexar con el modelo equivocado.
--
--    c) Las columnas text, metadata y embedding admiten NULL. El nodo no creo
--       ninguna restriccion de integridad.
--
--    Los nombres de columna son configurables desde el nodo (options > Column
--    Names); estos son los de fabrica.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- 3) Por que la leccion del modelo de embeddings es la que mas importa.
--
--    La columna no limita dimension, asi que hay que distinguir DOS casos y
--    NO son iguales:
--
--      Distinta dimension (1536 vs 768). Postgres corta con un error explicito:
--        ERROR: different vector dimensions 1536 and 768
--      Ruidoso. Facil de detectar y de arreglar.
--
--      MISMA dimension, distinto modelo (text-embedding-3-small vs
--      text-embedding-ada-002, ambos 1536). No hay error. Las distancias se
--      calculan, el ranking sale, el modelo responde con seguridad. Y es
--      basura, porque los dos vectores viven en sistemas de coordenadas que no
--      tienen ninguna relacion.
--
--    El caso peligroso es el segundo, y exige que las dimensiones COINCIDAN.
--    Por eso la regla es: el modelo de embeddings queda congelado en el momento
--    de indexar. Si lo cambias, reindexas todo.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- 4) Indice de similitud.
--
--    Comprobado sobre la base real: el nodo crea UNICAMENTE la clave primaria.
--    No crea indice de similitud. Con 3 fragmentos da igual, porque Postgres
--    recorre la tabla entera en microsegundos. Pero en un corpus real de miles
--    de filas, CADA consulta recorre todo y el RAG se vuelve lento.
--
--    Buena parte de "RAG que anda pero no escala" es exactamente esto.
--
--    HNSW aproxima la busqueda por vecinos mas cercanos. vector_cosine_ops tiene
--    que coincidir con la distancia configurada en el nodo (Cosine, el default).
--    Descomentalo y usa EXPLAIN ANALYZE antes y despues: es el ejercicio
--    avanzado que muestra la diferencia entre que funcione y que escale.
-- ---------------------------------------------------------------------------
-- CREATE INDEX IF NOT EXISTS n8n_vectors_embedding_hnsw_idx
--   ON n8n_vectors USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- 5) Chequeo rapido de que la extension quedo instalada.
--    Esto aparece en los logs del contenedor al levantar el stack.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    RAISE NOTICE 'OK: extension vector instalada (version %)',
      (SELECT extversion FROM pg_extension WHERE extname = 'vector');
  ELSE
    RAISE EXCEPTION 'FALLO: la extension vector no se instalo';
  END IF;
END
$$;
