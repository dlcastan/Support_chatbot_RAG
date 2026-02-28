import logging
import os
import json
import re
from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def evaluar_respuesta(pregunta: str, contexto: str, respuesta: dict) -> dict:

    try:
        client = OpenAI()

        respuesta_serializada = json.dumps(respuesta, ensure_ascii=False)

        prompt = f"""
Evalúa la siguiente respuesta de un sistema RAG.

Devuelve SOLO un JSON válido (sin bloques de código, sin texto adicional) con exactamente estas claves:

- score_total (número entero 0-10)
- relevance_score (número entero 0-10)
- precision_score (número entero 0-10)
- completeness_score (número entero 0-10)
- justification (string)

El campo "justification" debe:
- Tener al menos 50 caracteres.
- Mencionar explícitamente cuántos chunks del contexto fueron utilizados en la respuesta.
- Indicar si algún chunk fue ignorado o podría haber aportado más detalle.
- Ejemplo: "Puntaje 8: la respuesta usa 2 de los 3 chunks recuperados y responde la pregunta correctamente, pero no incorpora el detalle del chunk 3 sobre configuraciones avanzadas."

Pregunta:
{pregunta}

Contexto (chunks recuperados):
{contexto}

Respuesta generada:
{respuesta_serializada}
"""


        # Usamos Chat Completions en lugar de Responses API para mayor estabilidad
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        texto = response.choices[0].message.content.strip()

        # Limpiar posibles bloques de código ```json ... ```
        texto = re.sub(r"^```(?:json)?\s*", "", texto)
        texto = re.sub(r"\s*```$", "", texto)

        evaluacion = json.loads(texto)

        return evaluacion

    except json.JSONDecodeError as e:
        logger.error(f"No se pudo parsear el JSON de evaluación: {e}")
        logger.error(f"Texto recibido: {texto if 'texto' in dir() else 'N/A'}")
        return {
            "score_total": 0,
            "relevance_score": 0,
            "precision_score": 0,
            "completeness_score": 0,
            "justification": f"Error al parsear JSON: {str(e)}"
        }

    except Exception as e:
        logger.error("Error en evaluación automática")
        logger.error(str(e))
        return {
            "score_total": 0,
            "relevance_score": 0,
            "precision_score": 0,
            "completeness_score": 0,
            "justification": f"Error durante evaluación automática: {str(e)}"
        }