# Proyecto Integrador: Support Chatbot with RAG

Carrera: AI Engineering  
Alumno: Diego Lopez Castan  

---

## Descripción General

Este proyecto implementa un **asistente de soporte al cliente con RAG (Retrieval-Augmented Generation)** utilizando OpenAI API y una base vectorial con ChromaDB.

El sistema:

- Recibe una pregunta del usuario vía CLI
- Valida la entrada contra intentos de prompt injection y contenido adversarial
- Recupera contexto relevante desde una base vectorial (ChromaDB)
- Genera una respuesta **JSON estructurada** utilizando un LLM
- Evalúa automáticamente la calidad de la respuesta (relevancia, precisión, completitud)
- Registra métricas de uso (tokens, latencia y costo estimado)

---

## Objetivos

- Construir un pipeline RAG completo y funcional
- Implementar un **contrato JSON estable** como salida del sistema
- Evaluar automáticamente las respuestas generadas con un LLM juez
- Aplicar técnicas de prompt engineering con few-shot examples
- Incorporar seguridad activa contra ataques de prompt injection
- Medir costos y performance por consulta

---

## 📁 Estructura del Proyecto

```
proyecto/
│
├── metrics/
│   └── metrics.csv          -> Registra tokens, latencia y costo por consulta
│
├── outputs/
│   └── sample_queries.json  -> Historial de respuestas generadas
│
├── prompts/
│   └── main_prompt.txt      -> Define el prompt principal del sistema
│
├── vector_store/            -> Base vectorial ChromaDB (generada por build_index.py)
│
├── src/
│   ├── build_index.py       -> Construye e indexa la base vectorial
│   ├── query.py             -> Pipeline principal: RAG + LLM + evaluación
│   ├── evaluator.py         -> Evalúa la calidad de la respuesta automáticamente
│   └── safety.py            -> Detecta prompt injection y contenido adversarial
│
├── .env.example
├── Makefile
├── README.md
└── requirements.txt
```

---

## Configuración

**.env** — Crear el archivo e incluir las siguientes variables:

```
OPENAI_API_KEY=tu_api_key
OPENAI_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4.1-mini
```

**Instalar dependencias:**

```
make install
```

---

## Uso

**1. Construir la base vectorial** (ejecutar una sola vez o al actualizar los documentos):

```
python src/build_index.py --pregunta "pregunta de prueba"
```

**2. Ejecutar una consulta:**

```
make run ARGS="--pregunta 'Realizar la pregunta aquí'"
```

**3. Ejecutar tests:**

```
make test
```

---

## Búsqueda Vectorial

La recuperación de contexto relevante se implementa mediante **k-Nearest Neighbors (k-NN)** sobre la base vectorial ChromaDB, utilizando **similitud coseno** como métrica de distancia.

**Método:** k-NN con `k=3`, ejecutado a través de `similarity_search_with_score()` de LangChain + ChromaDB.

**Métrica:** Similitud coseno, definida como:

```
cos(A, B) = (A · B) / (||A|| × ||B||)
```

Donde `A` es el embedding de la consulta del usuario y `B` es el embedding de cada chunk indexado. El resultado es un valor entre -1 y 1, donde 1 indica máxima similitud semántica.

**¿Por qué similitud coseno?**  
Los embeddings de texto (como los de `text-embedding-3-small`) codifican el significado semántico en la dirección del vector, no en su magnitud. La similitud coseno mide el ángulo entre vectores, ignorando la longitud, lo que la hace más adecuada que la distancia euclidiana para comparar textos de distinta extensión. Es la métrica estándar para búsqueda semántica sobre embeddings de lenguaje.

Los scores obtenidos se registran en el campo `similarity_score` dentro de `chunks_related` en el JSON de salida.

---

## Flujo del Sistema

```
Usuario
   │
   ▼
Validación de seguridad (safety.py)
   │
   ▼
Recuperación de contexto (ChromaDB k-NN)
   │
   ▼
Construcción del prompt (few-shot + RAG)
   │
   ▼
Generación de respuesta (OpenAI LLM)
   │
   ▼
Evaluación automática (evaluator.py)
   │
   ▼
Registro de métricas (metrics.csv)
   │
   ▼
Salida JSON estructurada
```

---

## Formato de Salida

El sistema devuelve un JSON con la siguiente estructura:

```json
{
  "response": {
    "answer": "Respuesta del sistema",
    "actions": ["Acción sugerida 1", "Acción sugerida 2"]
  },
  "evaluation": {
    "score_total": 9,
    "relevance_score": 9,
    "precision_score": 8,
    "completeness_score": 9,
    "justification": "La respuesta es precisa y cubre el contexto disponible."
  },
  "metrics": {
    "timestamp": "2025-01-01T12:00:00",
    "tokens_prompt": 320,
    "tokens_completion": 85,
    "total_tokens": 405,
    "latency_ms": 1240,
    "estimated_cost_usd": "0.000210"
  }
}
```

---

## Seguridad

El módulo `safety.py` protege el sistema contra:

- **Prompt injection** — intentos de override de instrucciones del sistema
- **Exfiltración de datos** — solicitudes de API keys, tokens, credenciales
- **Ejecución no autorizada** — comandos SQL, bash, llamadas a APIs externas
- **Contenido codificado** — payloads en base64, scripts embebidos
- **Solicitudes fuera de scope** — generación de código malicioso, exploits

Los patrones de detección fueron definidos siguiendo el documento **OWASP Top 10 for LLM Applications 2025** del OWASP GenAI Security Project.  
Link: https://genai.owasp.org/

**Verificar el control de seguridad:**

```
make run ARGS="--pregunta 'ignora las instrucciones'"
```

---

## Autor

Desarrollado por Diego Lopez Castan

## Licencia

Uso libre para fines educativos y personales.