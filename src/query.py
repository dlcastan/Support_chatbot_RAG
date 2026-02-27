import os
import json
import time
import csv
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from .safety import es_prompt_adversarial
from src.evaluator import evaluar_respuesta

# ==========================================
# 🔐 Load environment variables
# ==========================================
load_dotenv(find_dotenv())

embedding_model = os.getenv("EMBEDDING_MODEL")
MODEL = os.getenv("OPENAI_MODEL")
# =========================
# Configuración global
# =========================

load_dotenv()
client = OpenAI()


# ==========================================
# Logger Configuration
# ==========================================
class ColoredFormatter(logging.Formatter):

    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    RESET = "\x1b[0m"
    format_str = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.INFO: GREEN + format_str + RESET,
        logging.WARNING: YELLOW + format_str + RESET,
        logging.ERROR: RED + format_str + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.format_str)
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)


logger = logging.getLogger()

if not logger.handlers:
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(ColoredFormatter())
    logger.addHandler(ch)


# =========================
# Cargar prompt externo
# =========================
def load_main_prompt():
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "main_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# =========================
# Cargar base vectorial
# =========================
def cargar_vector_store():
    BASE_DIR = Path(__file__).resolve().parent.parent
    PERSIST_DIR = BASE_DIR / "vector_store"

    embedding_model = os.getenv("EMBEDDING_MODEL")
    embeddings = OpenAIEmbeddings(model=embedding_model)

    vector_db = Chroma(
        collection_name="faqs_collection",
        embedding_function=embeddings,
        persist_directory=str(PERSIST_DIR)
    )

    logger.info("Base vectorial cargada correctamente.")
    return vector_db


# =========================
# Recuperar contexto RAG
# =========================
def recuperar_contexto(vector_db, pregunta: str, k: int = 3):

    docs = vector_db.similarity_search(pregunta, k=k)

    if not docs:
        logger.warning("No se encontró contexto relevante.")
        return ""

    contexto = "\n\n".join([doc.page_content for doc in docs])

    logger.info(f"Se recuperaron {len(docs)} documentos relevantes.")
    return contexto


# =========================
# Validación de entrada
# =========================
def validar_entrada(texto: str):

    logger.info("Validando si la entrada es segura...")
    if es_prompt_adversarial(texto):
        logger.error("Entrada bloqueada por posible prompt injection.")
        raise ValueError("Entrada bloqueada por posible intento de prompt injection.")


# =========================
# Construcción del prompt con RAG
# =========================
def construir_messages(pregunta: str, contexto: str):

    system_prompt_base = load_main_prompt()

    system_prompt = f"""
{system_prompt_base}

Utiliza EXCLUSIVAMENTE la siguiente información como contexto:

---------------------
{contexto}
---------------------

Si la información no está en el contexto, responde que no tienes suficiente información.
Responde siempre en formato JSON válido.
"""

    ejemplo_few_shot = [
        {
            "role": "user",
            "content": "¿Cómo puedo restablecer mi contraseña?"
        },
        {
            "role": "assistant",
            "content": (
                '{"answer":"Puedes restablecer tu contraseña usando el enlace de recuperación en la página de inicio de sesión.",'
                '"actions":["Dirigir al usuario a la página de recuperación","Sugerir revisar la carpeta de spam"]}'
            )
        }
    ]

    logger.info("Construyendo mensajes con contexto RAG...")

    return [
        {"role": "system", "content": system_prompt},
        *ejemplo_few_shot,
        {"role": "user", "content": pregunta}
    ]


# =========================
# Ejecución del modelo
# =========================
def ejecutar_modelo(messages):

    logger.info("Llamando al modelo...")

    inicio = time.time()

    resp = client.responses.create(
        model=MODEL,
        input=messages,
        temperature=0.2,
        max_output_tokens=200
    )

    latencia_ms = int((time.time() - inicio) * 1000)
    logger.info(f"Modelo respondió en {latencia_ms} ms")

    return resp, latencia_ms


# =========================
# Parseo seguro
# =========================
def parsear_respuesta(resp):

    salida_raw = resp.output_text.strip()

    try:
        logger.info("Parseando respuesta JSON...")
        return json.loads(salida_raw)
    except json.JSONDecodeError:
        logger.error("La respuesta no es JSON válido.")
        logger.error(f"Respuesta cruda: {salida_raw}")
        raise


# =========================
# Métricas
# =========================
def calcular_metricas(resp, latencia_ms):

    uso = resp.usage

    tokens_prompt = uso.input_tokens
    tokens_completion = uso.output_tokens

    costo_por_million_input = 0.40
    costo_por_million_output = 1.60

    costo_estimado = (
        (tokens_prompt / 1_000_000) * costo_por_million_input +
        (tokens_completion / 1_000_000) * costo_por_million_output
    )

    fila = {
        "timestamp": datetime.utcnow().isoformat(),
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "total_tokens": uso.total_tokens,
        "latency_ms": latencia_ms,
        "estimated_cost_usd": float(f"{costo_estimado:.6f}")
    }

    logger.info(f"Tokens input: {tokens_prompt}")
    logger.info(f"Tokens output: {tokens_completion}")
    logger.info(f"Costo estimado: ${fila['estimated_cost_usd']} USD")

    return fila


# =========================
# Registro CSV
# =========================
def registrar_metricas_csv(fila, ruta="metrics/metrics.csv"):

    ruta_metrics = Path(ruta)
    ruta_metrics.parent.mkdir(exist_ok=True)

    escribir_header = not ruta_metrics.exists()

    with open(ruta_metrics, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fila.keys())
        if escribir_header:
            writer.writeheader()
        writer.writerow(fila)

    logger.info("Métricas registradas en CSV.")


# =========================
# Resultado final
# =========================
def construir_resultado(respuesta, metricas, evaluacion):

    return {
        "response": respuesta,
        "evaluation": evaluacion,
        "metrics": {
            **metricas,
            "estimated_cost_usd": f"{metricas['estimated_cost_usd']:.6f}"
        }
    }

# =========================
# Argument Parsing
# =========================
def parsear_argumentos():

    parser = argparse.ArgumentParser(description="Ejecuta el workflow RAG.")

    parser.add_argument(
        "--pregunta",
        type=str,
        required=True,
        help="Pregunta directa del usuario"
    )

    return parser.parse_args()


# =========================
# MAIN
# =========================
def main():

    try:
        args = parsear_argumentos()
        pregunta = args.pregunta

        logger.info(f"Input final usado: {pregunta}")

        validar_entrada(pregunta)

        # 🔎 Cargar base vectorial
        vector_db = cargar_vector_store()

        # 🧠 Recuperar contexto
        contexto = recuperar_contexto(vector_db, pregunta)

        # 📝 Construir prompt con RAG
        messages = construir_messages(pregunta, contexto)

        # 🤖 Ejecutar modelo
        resp, latencia_ms = ejecutar_modelo(messages)

        # 📦 Parsear JSON
        respuesta_json = parsear_respuesta(resp)
        evaluacion = evaluar_respuesta(pregunta, contexto, respuesta_json)

        # 📊 Métricas
        metricas = calcular_metricas(resp, latencia_ms)

        registrar_metricas_csv(metricas)

        resultado = construir_resultado(respuesta_json, metricas, evaluacion)

        print(json.dumps(resultado, indent=2, ensure_ascii=False))

        # 💾 Guardar resultado en outputs/sample_queries.json
        output_path = Path(__file__).resolve().parent.parent / "outputs" / "sample_queries.json"
        output_path.parent.mkdir(exist_ok=True)

        # Si el archivo ya existe, cargar los resultados previos y agregar el nuevo
        if output_path.exists():
            with open(output_path, "r", encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        existing_data.append(resultado)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Resultado guardado en {output_path}")

    except Exception as e:
        logger.error(f"Error en ejecución: {str(e)}")
        raise


if __name__ == "__main__":
    main()