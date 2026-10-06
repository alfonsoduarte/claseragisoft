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
--    NO la creamos acá a propósito. La crea el propio nodo "Postgres PGVector
--    Store" la primera vez que inserta, y lo hace con exactamente la forma que
--    él espera. Si la declaramos nosotros y no coincide (tipo de la columna id,
--    dimensión, índice), los inserts fallan con errores difíciles de leer.
--
--    Lo que el nodo va a crear por vos, con los nombres por defecto de la
--    configuración del nodo (options > Column Names):
--
--      CREATE TABLE n8n_vectors (
--        id        text PRIMARY KEY,      -- id del chunk
--        embedding vector(1536) NOT NULL, -- 1536 = dimensión de text-embedding-3-small
--        text      text NOT NULL,         -- el chunk de texto
--        metadata  jsonb                  -- de dónde salió: archivo, fecha, etc.
--      );
--
--    Ese DDL es el que se documenta en docs/verificacion.md una vez comprobado
--    contra la base real. Los nombres de columna son configurables desde el nodo.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- 3) Índice de similitud: opcional.
--
--    Sin índice, Postgres recorre la tabla entera en cada consulta. Con pocos
--    cientos de chunks es instantáneo igual, así que NO hace falta para que la
--    clase funcione. Se lo puede dejar comentado y usar como ejercicio avanzado:
--    comparar el plan de ejecución (EXPLAIN ANALYZE) antes y después.
--
--    HNSW aproxima la búsqueda por vecinos más cercanos. `vector_cosine_ops`
--    tiene que coincidir con la distancia configurada en el nodo (Cosine).
-- ---------------------------------------------------------------------------
-- CREATE INDEX IF NOT EXISTS n8n_vectors_embedding_hnsw_idx
--   ON n8n_vectors USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- 4) Chequeo rápido de que la extensión quedó instalada.
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
