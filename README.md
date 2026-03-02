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
├── data/
│   └── faq_document.txt     -> Documento con la informacion a vectorizar
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
├── notebooks/
│   └── notebook.ipynb      -> Notebook con el proceso principal
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
OPENAI_MODEL=tu_modelo
EMBEDDING_MODEL=tu_modelo
```

**Instalar dependencias:**

```
make install
```

---

## Uso

**1. Construir la base vectorial** (ejecutar una sola vez o al actualizar los documentos):

```
python src/build_index.py
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

## ¿Por qué RAG?

Este sistema utiliza RAG (Retrieval-Augmented Generation) porque permite proporcionar información actualizada sin necesidad de reentrenar el modelo. En lugar de depender únicamente del conocimiento interno del LLM, el pipeline sigue dos pasos explícitos: primero **recupera** los chunks más relevantes desde la base vectorial (ChromaDB), y luego **genera** la respuesta condicionada exclusivamente a ese contexto.

Este enfoque resuelve tres problemas concretos:

- **Límite de tokens**: al pasar solo los chunks relevantes al modelo en lugar de toda la base de conocimiento, se mantiene el prompt dentro del límite de contexto del LLM.
- **Conocimiento actualizable**: para incorporar nueva información basta con reindexar documentos en el vector store, sin reentrenar ni modificar el modelo.
- **Transparencia**: cada respuesta puede trazarse hasta los chunks que la originaron, lo que hace el proceso auditable y reduce alucinaciones.

---

## Búsqueda Vectorial

La recuperación de contexto relevante se implementa mediante **k-Nearest Neighbors (k-NN)** sobre la base vectorial ChromaDB, utilizando **similitud coseno** como métrica de distancia.

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
      "user_question": "¿Qué tipo de conductas están prohibidas?",
      "system_answer": "Está prohibido usar la plataforma para actividades ilegales, fraudulentas, ofensivas o que vulneren derechos de terceros. También se prohíbe la distribución de contenido malicioso o spam.",
      "chunks_related": [
        "¿Qué tipo de conductas están prohibidas?\nEstá prohibido el uso de la plataforma para actividades ilegales, fraudulentas, ofensivas o que vulneren derechos de terceros. También se prohíbe la distribución de contenido malicioso o spam."
      ]
    },
    "evaluation": {
      "score_total": 9,
      "relevance_score": 10,
      "precision_score": 9,
      "completeness_score": 9,
      "justification": "La respuesta es altamente relevante y precisa, ya que reproduce fielmente el contenido del contexto sobre las conductas prohibidas. Sin embargo, podría mejorar ligeramente en completitud al mencionar explícitamente que estas conductas están prohibidas en la plataforma, aunque el mensaje es claro y completo en esencia."
    },
    "metrics": {
      "timestamp": "2026-02-27T19:55:49.229120",
      "tokens_prompt": 910,
      "tokens_completion": 129,
      "total_tokens": 1039,
      "latency_ms": 2695,
      "estimated_cost_usd": "0.000570"
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