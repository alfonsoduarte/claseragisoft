# Guion docente — Clase RAG en n8n

Este documento no explica n8n. Explica **cómo contar RAG** para que los alumnos se lleven
una idea que no se les borra, y de paso construyan algo que funcione.

---

## 1. La única idea que tienen que llevarse

Si al final de la clase pudieran recordar una sola frase, que sea esta:

> **Un modelo generativo no sabe nada de tus documentos. Y "darle tus documentos" no es
> magia: es un pipeline de dos mitades —indexar y consultar— que puede fallar en silencio.**

Todo lo demás (nodos, credenciales, chunkSize) son detalles al servicio de esa frase.

---

## 2. Antes de empezar: checklist

Que esto esté resuelto **antes** de que entre el primer alumno. Una demo caída al
minuto cinco te cuesta el resto de la clase.

```bash
cd clase-rag/docker
docker compose ps                  # los 3 contenedores "Up" y "healthy"
docker exec clase-rag-vectorstore psql -U raguser -d ragdb \
  -tAc "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

- [ ] Los 3 contenedores arriba.
- [ ] `vector 0.8.7` responde.
- [ ] Las 3 credenciales cargadas y **asignadas en los nodos** de ambos workflows.
- [ ] Ya indexaste el corpus al menos una vez (así no lo hacés en vivo por primera vez).
- [ ] Tenés los 3 PDFs de `dataset/` a mano en el escritorio.
- [ ] **Tenés una ventana privada abierta en `http://localhost:5679`** (la cookie `n8n-auth`
      no distingue puerto: si usás tu navegador normal te pisa la sesión de tu otro n8n).
- [ ] Base limpia, si querés arrancar de cero: `TRUNCATE n8n_vectors;`

---

## 3. El arco narrativo

Cinco bloques. No los mezcles: cada uno responde una pregunta distinta.

| Bloque | La pregunta del alumno | La respuesta |
| --- | --- | --- |
| 1. El fracaso (8 min) | "¿Por qué no le pregunto directo al chat?" | Porque te va a mentir con seguridad |
| 2. Los embeddings (15 min) | "¿Cómo encuentra algo que no busca por palabras?" | Busca por cercanía de significado |
| 3. La ingesta (30 min) | "¿Qué hace exactamente al guardar?" | Corta, convierte a números y almacena |
| 4. La consulta (25 min) | "¿Cómo arma la respuesta?" | Recupera 4 fragmentos y responde sólo con eso |
| 5. Los límites (20 min) | "¿Y esto cuándo falla?" | Falla callado, y ahí está el oficio |

---

## 4. Bloque por bloque

### Bloque 1 — El fracaso (8 min)

**No expliques nada todavía.** Abrí el workflow 02 con la base **vacía** y hacé esta
pregunta en el chat, delante de todos:

> "¿Cuánto dura la garantía estándar según el Manual de Operaciones de Talleres Rivadavia?"

Es un dato real que está en el PDF (`18 meses`). El agente va a responder una de dos cosas:
o inventa un número plausible, o dice que no sabe.

**Cualquiera de las dos sirve. Si inventa, es mejor.**

Ahí decís, textual:

> "Ese dato existe. Está en un PDF que la empresa tiene. El modelo lo acaba de inventar
> con total seguridad, y no hay forma de que ustedes lo detecten leyendo la respuesta.
> Ahora vamos a arreglarlo. Pero no lo vamos a arreglar pidiéndole que sea más honesto:
> lo vamos a arreglar cambiando **de dónde saca la información**."

**Frase para cerrar el bloque:**

> "Un modelo no es una base de datos. Es una máquina de continuar texto de forma verosímil.
> Verosímil y verdadero no son lo mismo."

### Bloque 2 — Los embeddings (15 min)

Este es el bloque donde se gana o se pierde la clase. Si lo explicás mal, el resto es
recetas.

**Arrancá por el problema, no por la definición:**

> "Si yo quiero buscar en este PDF la respuesta a '¿cuánto dura la garantía?', la forma
> obvia es buscar la palabra 'garantía'. Pero el documento podría decir 'cobertura',
> 'vigencia' o 'plazo de respaldo'. La búsqueda por texto exacto falla. Necesitamos algo
> que capture el **significado**, no las letras."

**Ahora la definición:**

> "Un embedding es una función que toma un texto y lo convierte en una lista de 1536
> números. Nada más. La propiedad que lo hace útil es esta: dos textos que hablan de lo
> mismo quedan **cerca** en ese espacio de 1536 dimensiones. Dos textos que hablan de cosas
> distintas quedan **lejos**."

**El mapa de 1536 dimensiones.** Usá esta analogía:

> "Piensen un mapa. Cada texto es un punto. 'Garantía' y 'cobertura' caen en el mismo
> barrio. 'Garantía' y 'presupuesto de pintura' caen lejos. Buscar es preguntar: decime
> los 4 puntos más cercanos a este."

**La trampa de la analogía — decila vos antes de que la descubran ellos:**

> "Dos advertencias. Primero: no es un mapa de dos dimensiones, son 1536, y nadie puede
> mirarlo ni interpretar qué significa cada eje. Segundo, y más importante: la cercanía es
> **estadística, no semántica de verdad**. Si el corpus nunca habla de tu tema, el vector
> más cercano igual va a existir, y va a estar lejos. La base no te dice 'no tengo nada
> parecido'; te devuelve los 4 menos malos. Ese es el origen de la mitad de los fracasos
> de RAG."

**Y acá hacés la primera demo técnica** (ver §7, demo 3): mostrar los 1536 números crudos
en la base. Cuando ven la lista de decimales, los embeddings dejan de ser un concepto
abstracto y pasan a ser un dato que pueden tocar.

### Bloque 3 — La ingesta (30 min)

Recorré el workflow 01 **de izquierda a derecha**, y en cada nodo preguntá antes de
mostrar: *"¿qué creen que hace esto?"*

| Nodo | Lo que tenés que decir |
| --- | --- |
| Formulario | "Un trigger es simplemente 'qué hace arrancar esto'. Acá, que alguien suba un PDF." |
| Extraer texto del PDF | "Un PDF no es texto, es un formato de impresión. Primero hay que sacarle las letras. **Este nodo puede devolver vacío y no avisar.** Guarden eso para el bloque 5." |
| Cargar documento | "Acá se agrega la metadata: de qué archivo salió, quién lo subió, cuándo. Sin metadata podés responder bien pero no podés auditar de dónde salió. La metadata es lo que hace que esto sea un sistema y no una demo." |
| Dividir en fragmentos | "El corazón conceptual del bloque. Lo vemos abajo." |
| Embeddings OpenAI | "Acá los fragmentos se convierten en los 1536 números de los que hablamos." |
| Guardar en pgvector | "Y acá se guardan. Postgres con una extensión que entiende vectores." |

**El chunking merece cinco minutos propios.** Dos preguntas para hacerles, en este orden:

1. *"¿Por qué no guardamos el documento entero como un solo vector?"*

Que ellos intenten responder. Después completá con las dos razones reales:

> "Dos problemas. Uno: el modelo tiene un límite de contexto, no le entra un manual entero.
> Dos, y más sutil: si metés todo un manual en **un** vector, ese vector es el promedio de
> todo el manual, y entonces no se parece a nada en particular. La búsqueda se vuelve
> imprecisa. Fragmentar no es una limitación técnica: es una decisión de calidad de
> búsqueda."

2. *"¿Y por qué el solapamiento (overlap)?"*

> "Porque las ideas no respetan los cortes. Si cortás exacto en el límite, podés partir una
> regla al medio y dejar la condición en un fragmento y la consecuencia en el siguiente.
> Ninguno de los dos sirve para responder. El solapamiento de 150 caracteres garantiza que
> una idea que cruza el borde aparezca completa en algún fragmento."

**Y decí esto, que es lo que se llevan a la práctica:**

> "`chunkSize: 1000` y `chunkOverlap: 150` no son valores sagrados. Son un punto de
> partida. Documentos muy técnicos piden fragmentos más chicos; documentos narrativos
> toleran más grandes. Esto se ajusta probando, y lo vamos a probar en el bloque 5."

### Bloque 4 — La consulta (25 min)

Volvé al workflow 02, que ahora sí tiene datos. Recorré el camino de una pregunta:

1. El chat recibe la pregunta.
2. **La pregunta se convierte en un vector con el MISMO modelo de embeddings.** Este es el
   punto que hay que martillar (ver §8).
3. El agente usa la herramienta `base_conocimiento` para pedir los 4 fragmentos más
   cercanos (`topK: 4`).
4. Le pasa esos 4 fragmentos al modelo como contexto, junto con el system prompt.
5. El modelo redacta la respuesta.

**Mostrá el system prompt en pantalla y leelo en voz alta.** Es la pieza que casi nadie
mira y es la que separa RAG de un chatbot que alucina:

> "Miren lo que le pedimos. Cuatro reglas: respondé **sólo** con lo que está en esos
> fragmentos; si no está, decí que no encontraste; **decí de qué archivo salió**; y si los
> fragmentos se contradicen, mostralo en lugar de elegir. Eso es *grounding*: no es que el
> modelo sea más honesto, es que le cambiamos el insumo y le restringimos la salida."

**Preguntá de nuevo lo del bloque 1.** Ahora responde `18 meses` y dice de qué archivo
salió. Ahí cerrás:

> "¿Qué cambió? No cambiamos el modelo. Es el mismo DeepSeek. Cambiamos **de dónde saca la
> información**."

**Ahora hacé la pregunta que no está en ningún documento:**

> "¿Cuánto sale el envío internacional?"

El agente debe negarse. Si se niega, ya está. Si inventa, revisá el prompt en vivo: es una
oportunidad, no un accidente.

**Una nota sobre `topK` que vale decir:**

> "Le pedimos 4 fragmentos. Si le pido 1, me arriesgo a que el fragmento bueno no sea el
> primero y la respuesta se pierda. Si le pido 20, le lleno el contexto de ruido y el modelo
> se distrae. 4 es un compromiso razonable. Y ojo: 'más parecido' no es 'más verdadero'."

### Bloque 5 — Los límites (20 min)

Este bloque es el que distingue una clase de un tutorial. Acá no se construye nada: se
rompe.

**Fracaso 1 — el PDF escaneado.**

Subí `03-acta-escaneada.pdf`. El workflow **va a decir que salió bien**. No hay error, no
hay alerta. Después preguntá por el contenido del acta:

> "¿Por qué se rechazó el lote L-2026-014?"

No lo va a poder responder. Ahí mostrá la causa:

```bash
docker exec clase-rag-vectorstore psql -U raguser -d ragdb \
  -c "SELECT metadata->>'archivo' AS archivo, count(*), sum(length(text)) AS caracteres
      FROM n8n_vectors GROUP BY 1;"
```

El acta va a aparecer con **0 caracteres**. La frase para dejar picando:

> "En RAG el fracaso más común es **silencioso**. El sistema no falla: indexa vacío y sigue
> contento. Si ustedes no verifican, esto llega a producción y nadie se enteró."

**Fracaso 2 — el error que van a cometer ellos.**

Este es el momento más valioso de la clase. Antes de arrancar, decí esto y escribilo en
la pizarra:

> "Hay dos maneras de equivocarse con el modelo de embeddings, y **no son igual de
> peligrosas**. Una grita. La otra te deja pasar."

**Caso A — distinta dimensión.** Cambiá el modelo del workflow 02 a uno de otra
 dimensión (768, por ejemplo) y preguntá. Postgres corta en seco:

```text
ERROR: different vector dimensions 1536 and 768
```

> "Ruidoso. Molesto, cinco minutos y listo. Un error explícito es una bendición."

**Caso B — la misma dimensión, otro modelo.** Volvé a `text-embedding-3-small` en la
ingesta, y en el **workflow 02** poné `text-embedding-ada-002`. Los dos son de 1536
 dimensiones, así que la base no va a decir nada. Preguntá lo mismo de siempre.

**Va a devolver una respuesta.** Va a sonar razonable. Va a estar mal. Y no hay log rojo,
ni excepción, ni nada.

> "Acá está la trampa. Los dos modelos producen vectores de 1536 números, pero **no hay
> ninguna relación entre las coordenadas de uno y las del otro**. Es como comparar
> distancias en un mapa con distancias en otro mapa distinto y creer que significan lo
> mismo. Las restas se hacen, el ranking sale, y es basura."

**Y ahora la regla, que es lo que se llevan:**

> "El caso peligroso exige que las dimensiones **coincidan**. Cuando no coinciden, la base
> te protege. Cuando coinciden y el modelo es otro, nadie te protege. Por eso: **el modelo
> de embeddings queda congelado en el momento en que indexás**. Si lo cambiás, reindexás
> todo. No es una recomendación de estilo, es la única forma."

**Preguntá después:** *"¿Cómo se protegerían de esto en un sistema real?"* La respuesta que
buscás: guardar el nombre del modelo en la metadata de cada fragmento y verificar que
coincida con el de la consulta antes de responder, en lugar de confiar en la base.

Si el tiempo alcanza, hacé el ejercicio 3 de §10: bajar `chunkSize` a 300 y ver cómo cambia
la calidad de las respuestas.

---

## 5. Los seis conceptos, en este orden

El orden no es decorativo. Cada uno necesita el anterior.

1. **El problema** — el modelo no conoce tus documentos.
2. **Embeddings** — texto → vector; cerca = parecido en significado.
3. **Chunking** — fragmentar es una decisión de calidad, no una limitación.
4. **Recuperación** — de la pregunta saco K vecinos; "más parecido" ≠ "más verdadero".
5. **Grounding** — sólo el contexto recuperado, o admite que no sabe.
6. **Arquitectura: dos planos** — ingesta y consulta son ciclos de vida distintos, y eso
   obliga a tener un almacén externo y durable.

**El sexto es el que convierte esto en arquitectura.** No lo saltees ni lo dejes para el
final apurados. Decilo así:

> "Podríamos hacer todo en un solo workflow. n8n tiene un `Simple Vector Store` que hace
> exactamente eso, y hay un template oficial. Pero no lo vamos a usar, y quiero que quede
> claro por qué. Esa memoria **vive dentro de la ejecución**. La documentación del propio
> nodo dice que se pierde en los reinicios y que `puede vaciarse si la memoria disponible
> baja`. Si la ponés en un workflow, no la puede leer otro.

> Ingestionar y consultar no son la misma cosa. Corren en momentos distintos, con ritmos
> distintos, y tienen requisitos distintos: la ingesta puede tardar y ser lenta; la consulta
> tiene que ser rápida porque hay un humano esperando. Son dos planos. Y separar planos no
> es gratis: **te obliga a tener un almacén compartido y durable**. Ese almacén es pgvector,
> y ese es el precio real de la decisión."

---

## 6. Analogías: cuáles sirven y cuál te va a traicionar

| Concepto | Analogía que funciona |
| --- | --- |
| Embeddings | Un mapa donde cada texto es un punto y los temas afines son barrios |
| Retrieval | Un bibliotecario que te trae los 4 párrafos más relevantes, no el libro entero |
| Grounding | Un becario brillante y con mala memoria al que le ponés los papeles en la mano **justo antes** de que responda, y le prohibís inventar |
| Chunking | No indexás el libro, indexás párrafos; si un párrafo mezcla dos temas, el índice miente |

**La analogía que te va a traicionar:** decir que los embeddings "entienden" el texto. No
entienden nada. Son una función estadística. Si los alumnos se van creyendo que hay
comprensión, después no van a poder explicar por qué el sistema devuelve basura cuando el
corpus no cubre el tema. La versión correcta es: *"capturan regularidades estadísticas, y
eso es suficiente para buscar, pero no es comprensión."*

---

## 7. Guion de demos

**Demo 1 — el fracaso.** Workflow 02 con la base vacía. Preguntar por la garantía.

**Demo 2 — la ingesta.** Workflow 01. Abrir la URL del formulario, subir
`01-manual-operaciones.pdf`, poner origen "Manual de operaciones". Mostrar el formulario
**desde el navegador de los alumnos si se puede**, porque ver el formulario real hace que
la demo deje de ser abstracta.

**Demo 3 — mirar por dentro.** La demo que hace que todo lo anterior sea concreto:

```bash
docker exec -it clase-rag-vectorstore psql -U raguser -d ragdb
```

```sql
-- Cuántos fragmentos se generaron a partir de un solo PDF
SELECT count(*) FROM n8n_vectors;

-- Los fragmentos, con su archivo de origen
SELECT metadata->>'archivo' AS archivo,
       left(text, 70)      AS fragmento
FROM n8n_vectors
ORDER BY metadata->>'archivo', id;

-- Los 1536 números. Esto es un embedding.
SELECT left(embedding::text, 90) || ' ...' AS primeros_numeros
FROM n8n_vectors LIMIT 1;

-- Y sí, son 1536
SELECT vector_dims(embedding) FROM n8n_vectors LIMIT 1;
```

Decí esto mientras corren las consultas:

> "Eso de ahí es lo que hicimos. Un PDF entró, salió cortado en pedazos, cada pedazo se
> convirtió en 1536 números y quedó guardado acá. Nada de esto es magia, y ustedes pueden
> auditarlo con una consulta SQL."

**Demo 4 — la consulta.** Workflow 02, la misma pregunta del bloque 1. Respuesta fundada
con cita del archivo.

**Demo 5 — la negativa.** Preguntar algo que no está. Debe negarse.

**Demo 6 — el escaneado.** Subir `03-acta-escaneada.pdf`, preguntar por el acta, fallar, y
mostrar los 0 caracteres con la consulta agregada.

**Demo 7 — el embudo de la decisión.** Hacer que la clase vote: *"si tuvieran que indexar
5000 PDFs de una empresa, ¿qué cambiarían de lo que hicimos?"* Las respuestas correctas
apuntan a: topK y chunking por tipo de documento, metadata más rica, reindexado, y un
evaluador en vez de "a ojo".

---

## 8. Los errores que conviene dejar que ocurran

No los prevengas. El aprendizaje está en el diagnóstico.

| Error | Por qué conviene dejarlo pasar |
| --- | --- |
| Poner `localhost` en la credencial de Postgres | Es el error #1. `localhost` dentro de n8n es el propio contenedor. Tiene que ser `vectorstore`. Se arregla en 10 segundos y se recuerda para siempre. |
| Cambiar el embedding entre ingesta y consulta | El error silencioso, **siempre que las dimensiones coincidan**. Si no coinciden, Postgres avisa. Ver bloque 5, caso B. |
| Crear la credencial y no asignarla en el nodo | El más común de todos, y el más frustrante: dice "no credentials" y parece que la credencial no sirviera. |
| Subir un PDF escaneado | Falla sin avisar. Deja la lección: en RAG el fracaso es silencioso. |
| Subir el mismo PDF dos veces | Duplica fragmentos. La `id` es un `uuid` que genera Postgres en cada insert, así que nunca colisiona y nunca reemplaza. Se arregla con un `doc_id` estable en la metadata; no lo agregué al workflow a propósito, para que sea el ejercicio de mejora. |
| Poner `chunkOverlap` mayor que `chunkSize` | Genera fragmentos duplicados. Buen bug para que experimenten. |

---

## 9. Plan B: si algo se rompe en vivo

| Síntoma | Qué decís y qué hacés |
| --- | --- |
| El formulario da 404 | El workflow no está activo. Es el único paso que hay que hacer con el toggle de la UI. Si no toma, reiniciá el contenedor. |
| Error de credencial | No la asignaste en el nodo. Elegila del desplegable; no alcanza con crearla. |
| `getaddrinfo EAI_AGAIN vectorstore` | El contenedor de la base vectorial no está en la misma red. `docker compose ps` y revisar que esté arriba. |
| No devuelve nada y no hay error | Es el caso del PDF escaneado. Es la lección, no un bug. |
| El chat no responde | Verificá que las dos API keys tengan saldo. Es la causa más común. |
| Se cae la demo entera | Tené el `SELECT * FROM n8n_vectors` de una corrida previa a mano. La lección se puede dar igual: los vectores ya están en la base. |

---

## 10. Tarea para los alumnos

Entregable: los dos workflows exportados como JSON, más un documento de media página.

1. **Replicar.** Levantar el entorno con `docker compose up -d`, cargar las credenciales,
   importar ambos workflows e indexar el manual. Entregar los dos JSON exportados.
2. **Auditar.** Pegar la salida de `SELECT count(*) FROM n8n_vectors;` y de la consulta que
   muestra los fragmentos. ¿Cuántos fragmentos salieron de un PDF de 2 páginas?
3. **Explicar el fracaso.** ¿Qué pasó al subir el PDF escaneado y por qué el sistema **no**
   dio ningún error? Esta es la pregunta que importa.
4. **Romperlo.** Cambiar `chunkSize` a 300, reindexar y comparar la calidad de las
   respuestas. ¿Mejoró, empeoró o dio igual? ¿Con qué evidencia lo afirman?
5. **Mejorar (opcional).** Volver idempotente la ingesta: que subir dos veces el mismo
   archivo no duplique los fragmentos. Pista: la metadata ya tiene el nombre del archivo.

Pregunta 3 es la que separa a quien entendió el arco de quien copió los nodos.

---

## 11. Lo que te van a preguntar

**"¿No conviene fine-tuning en vez de RAG?"**
> "Son cosas distintas. El fine-tuning enseña **estilo y formato**, no hechos nuevos, y es
> caro y hay que rehacerlo cuando cambia el documento. RAG le da **información** que podés
> actualizar subiendo otro PDF. Para conocimiento que cambia, RAG."

**"¿Y si pego el documento entero en el prompt?"**
> "Con un PDF de 2 páginas funciona. Con 500 documentos de una empresa no entra, y aunque
> entrara, pagarías el contexto completo en cada pregunta y el modelo se distraería. RAG es
> un filtro: le mandás los 4 fragmentos que importan, no todo."

**"¿Cómo sé que las respuestas son correctas?"**
> "Esa es la pregunta de producción y la más honesta que pueden hacer. La respuesta corta es
> que necesitás un evaluador con preguntas y respuestas conocidas, y medir cuántas acierta.
> Nosotros no lo construimos hoy, y quiero que sepan que es el paso siguiente, no un
> detalle."

**"¿Cuánto cuesta esto?"**
> "Indexar es casi gratis: convertir un documento de 50 páginas a vectores cuesta fracciones
> de centavo. El gasto real está en la consulta, porque cada pregunta paga el modelo
> generativo. Por eso conviene un modelo barato para el chat y no el más caro del mercado."

**"¿Esto es IA?"**
> "Sí, pero la parte inteligente es más chica de lo que parece. La parte difícil de lo que
> hicimos es ingeniería: fragmentar bien, guardar metadata, separar planos, verificar. El
> modelo es una pieza; el sistema alrededor es el trabajo."

---

## 12. Cómo explicarlo en una pizarra, en 60 segundos

Si te quedan cinco minutos y querés el resumen máximo:

```
   PDF ──► cortar ──► números ──► [ pgvector ]
                                      ▲
                                      │ los 4 más cercanos
                                      │
   pregunta ──► números ──────────────┘
                    │
                    ▼
              contexto + pregunta ──► modelo ──► respuesta + cita
```

Y debajo, en letra grande:

> **"El modelo no sabe. Le damos los papeles justo antes de responder, y le prohibimos inventar."**
