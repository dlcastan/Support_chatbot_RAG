import os
import json
import time
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma

# ==========================================
# 🔧 Logging
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ==========================================
# 🔐 Load env
# ==========================================
load_dotenv(find_dotenv())

embedding_model = os.getenv("EMBEDDING_MODEL")
chat_model = os.getenv("CHAT_MODEL")

if not embedding_model or not chat_model:
    raise ValueError("EMBEDDING_MODEL o CHAT_MODEL no están definidos en .env")

# ==========================================
# 📁 Paths robustos
# ==========================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "sample_queries.json"

# ==========================================
# 📥 Argumentos CLI
# ==========================================
parser = argparse.ArgumentParser()
parser.add_argument("--pregunta", type=str, required=True)
args = parser.parse_args()

user_question = args.pregunta.strip()
logger.info(f"Pregunta recibida: {user_question}")

# ==========================================
# 🧠 Embeddings
# ==========================================
embeddings = OpenAIEmbeddings(model=embedding_model)

# ==========================================
# 📚 Cargar base vectorial
# ==========================================
if not VECTOR_STORE_DIR.exists():
    raise FileNotFoundError("No existe vector_store. Ejecutá primero build_index.py")

vector_db = Chroma(
    persist_directory=str(VECTOR_STORE_DIR),
    embedding_function=embeddings
)

logger.info("Base vectorial cargada correctamente.")

# ==========================================
# 🔎 Búsqueda vectorial k-NN
# ==========================================
k = 3
start_time = time.time()

results = vector_db.similarity_search_with_score(user_question, k=k)

latency_ms = int((time.time() - start_time) * 1000)

logger.info(f"Se recuperaron {len(results)} documentos relevantes.")

chunks_related = []
context_parts = []

for doc, score in results:
    chunks_related.append({
        "content": doc.page_content,
        "similarity_score": float(score)
    })
    context_parts.append(doc.page_content)

context = "\n\n".join(context_parts)

# ==========================================
# 🤖 LLM
# ==========================================
llm = ChatOpenAI(
    model=chat_model,
    temperature=0
)

prompt = f"""
Responde únicamente utilizando la información del contexto.

Contexto:
{context}

Pregunta:
{user_question}

Si no hay información suficiente, indícalo claramente.
"""

logger.info("Llamando al modelo...")

response = llm.invoke(prompt)
system_answer = response.content.strip()

logger.info("Modelo respondió correctamente.")

# ==========================================
# 📦 Construcción JSON final
# ==========================================
final_output = {
    "response": {
        "user_question": user_question,
        "system_answer": system_answer,
        "chunks_related": chunks_related
    },
    "metrics": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
        "total_chunks_retrieved": len(results)
    }
}

# ==========================================
# 💾 Guardar archivo JSON (FORZADO)
# ==========================================
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    logger.info(f"Archivo JSON guardado correctamente en: {OUTPUT_FILE}")

except Exception as e:
    logger.error(f"Error al guardar JSON: {e}")
    raise

# ==========================================
# 🖥 Mostrar salida en consola
# ==========================================
print(json.dumps(final_output, indent=2, ensure_ascii=False))