import re


def es_prompt_adversarial(texto: str) -> bool:
    """
    Detecta si el texto contiene patrones asociados a prompt injection,
    exfiltración de datos, ejecución no autorizada o intentos de override
    de reglas del sistema.

    :param texto: Input del usuario.
    :return: True si se considera adversarial, False si no.
    """

    if not texto:
        return False

    texto_lower = texto.lower()

    # =========================
    # 1. Intentos de override del sistema
    # =========================
    patrones_override = [
        r"ignora (las )?instrucciones",
        r"olvida (las )?instrucciones",
        r"actúa como",
        r"you are now",
        r"system prompt",
        r"override",
        r"reveal your instructions",
        r"muestra tus reglas",
        r"internal rules",
    ]

    # =========================
    # 2. Intentos de exfiltración
    # =========================
    patrones_exfiltracion = [
        r"api[_\- ]?key",
        r"token",
        r"password",
        r"credentials?",
        r"connection string",
        r"database dump",
        r"export all data",
        r"full dataset",
        r"private data",
        r"datos internos",
    ]

    # =========================
    # 3. Intentos de ejecución
    # =========================
    patrones_ejecucion = [
        r"execute sql",
        r"run this query",
        r"delete from",
        r"drop table",
        r"shell command",
        r"bash",
        r"curl http",
        r"wget",
        r"send email",
        r"call api",
        r"modify user role",
        r"access database",
    ]

    # =========================
    # 4. Contenido codificado sospechoso
    # =========================
    patrones_encoded = [
        r"base64",
        r"atob\(",
        r"<script>",
        r"<!--",
        r"```",
    ]

    # =========================
    # 5. Solicitudes fuera de scope (no soporte)
    # =========================
    patrones_fuera_scope = [
        r"write a poem",
        r"generate code",
        r"create malware",
        r"hack",
        r"exploit",
        r"penetration test",
    ]

    todos_patrones = (
        patrones_override
        + patrones_exfiltracion
        + patrones_ejecucion
        + patrones_encoded
        + patrones_fuera_scope
    )

    for patron in todos_patrones:
        if re.search(patron, texto_lower):
            return True

    return False
