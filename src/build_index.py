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
# Logging
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ==========================================
# Paths robustos
# ==========================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR = PROJECT_ROOT / "vector_store"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_FILE = OUTPUT_DIR / "sample_queries.json"


# ==========================================
# Carga de variables de entorno
# ==========================================
def load_env() -> tuple[str, str]:
    load_dotenv(find_dotenv())
    embedding_model = os.getenv("EMBEDDING_MODEL")
    chat_model = os.getenv("CHAT_MODEL")
    if not embedding_model or not chat_model:
        raise ValueError("EMBEDDING_MODEL o CHAT_MODEL no están definidos en .env")
    return embedding_model, chat_model


# ==========================================
# Argumentos CLI
# ==========================================
def parse_args() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pregunta", type=str, required=True)
    args = parser.parse_args()
    return args.pregunta.strip()


# ==========================================
# Inicialización de embeddings
# ==========================================
def load_embeddings(embedding_model: str) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=embedding_model)


# ==========================================
# Carga de base vectorial
# ==========================================
def load_vector_store(embeddings: OpenAIEmbeddings) -> Chroma:
    if not VECTOR_STORE_DIR.exists():
        raise FileNotFoundError("No existe vector_store. Ejecutá primero build_index.py")
    vector_db = Chroma(
        persist_directory=str(VECTOR_STORE_DIR),
        embedding_function=embeddings
    )
    logger.info("Base vectorial cargada correctamente.")
    return vector_db


# ==========================================
# Búsqueda vectorial k-NN
# ==========================================
def search_similar_chunks(vector_db: Chroma, question: str, k: int = 3) -> tuple[list, int]:
    start_time = time.time()
    results = vector_db.similarity_search_with_score(question, k=k)
    latency_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Se recuperaron {len(results)} documentos relevantes.")
    return results, latency_ms


# ==========================================
# Construcción de contexto y chunks
# ==========================================
def build_context(results: list) -> tuple[str, list]:
    chunks_related = []
    context_parts = []
    for doc, score in results:
        chunks_related.append({
            "content": doc.page_content,
            "similarity_score": float(score)
        })
        context_parts.append(doc.page_content)
    context = "\n\n".join(context_parts)
    return context, chunks_related


# ==========================================
# Llamada al LLM
# ==========================================
def query_llm(chat_model: str, context: str, question: str) -> str:
    llm = ChatOpenAI(model=chat_model, temperature=0)
    prompt = f"""
Responde únicamente utilizando la información del contexto.

Contexto:
{context}

Pregunta:
{question}

Si no hay información suficiente, indícalo claramente.
"""
    logger.info("Llamando al modelo...")
    response = llm.invoke(prompt)
    logger.info("Modelo respondió correctamente.")
    return response.content.strip()


# ==========================================
# Construcción del JSON final
# ==========================================
def build_output(question: str, answer: str, chunks: list, latency_ms: int) -> dict:
    return {
        "response": {
            "user_question": question,
            "system_answer": answer,
            "chunks_related": chunks
        },
        "metrics": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency_ms": latency_ms,
            "total_chunks_retrieved": len(chunks)
        }
    }


# ==========================================
# Guardado del JSON
# ==========================================
def save_output(data: dict) -> None:
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Archivo JSON guardado correctamente en: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Error al guardar JSON: {e}")
        raise


# ==========================================
# Main
# ==========================================
def main():
    embedding_model, chat_model = load_env()
    user_question = parse_args()
    logger.info(f"Pregunta recibida: {user_question}")

    embeddings = load_embeddings(embedding_model)
    vector_db = load_vector_store(embeddings)

    results, latency_ms = search_similar_chunks(vector_db, user_question)
    context, chunks_related = build_context(results)

    system_answer = query_llm(chat_model, context, user_question)

    final_output = build_output(user_question, system_answer, chunks_related, latency_ms)

    save_output(final_output)
    print(json.dumps(final_output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()