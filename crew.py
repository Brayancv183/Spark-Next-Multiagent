import json
import os
import re
import time
import logging
from groq import Groq
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

from agents.greeting_agent import crear_agente_saludo
from agents.query_agent import crear_agente_consulta
from agents.retention_agent import crear_agente_retencion
from agents.verifier_agent import crear_agente_verificador
from agents.analytics_agent import crear_agente_analitico
from tools.client_lookup_tool import buscar_cliente, buscar_problema, buscar_termino_en_problemas, registrar_cliente

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY no esta definida en el entorno")

cliente_groq = Groq(api_key=GROQ_API_KEY)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORIAL_CLIENTES_PATH = os.path.join(DATA_DIR, "historial_clientes.json")

MEMORIA = {}
CLIENTES_VERIFICADOS = {}
METRICAS = {
    "total_conversaciones": 0,
    "por_intento": {"saludo": 0, "consulta": 0, "queja": 0},
    "por_agente": {"saludo": 0, "consulta": 0, "retencion": 0, "verificador": 0},
    "sentimientos": {"positivo": 0, "neutro": 0, "negativo": 0},
    "idiomas": {"es": 0, "en": 0},
    "quejas_detectadas": 0,
    "clientes_insatisfechos": 0,
    "problemas_reportados": {},
}


def cargar_historial_clientes():
    if not os.path.exists(HISTORIAL_CLIENTES_PATH):
        return {}
    try:
        with open(HISTORIAL_CLIENTES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error leyendo {HISTORIAL_CLIENTES_PATH}: {e}")
        return {}


def guardar_historial_clientes(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORIAL_CLIENTES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def registrar_incidencia_cliente(cedula, nombre, tipo_problema, descripcion, mensaje_usuario):
    historial = cargar_historial_clientes()
    if cedula not in historial:
        historial[cedula] = {"nombre": nombre, "incidencias": []}
    historial[cedula]["incidencias"].append({
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tipo": tipo_problema,
        "descripcion": descripcion,
        "mensaje_cliente": mensaje_usuario[:200],
    })
    guardar_historial_clientes(historial)


def obtener_incidencias_cliente(cedula):
    historial = cargar_historial_clientes()
    if cedula not in historial or not historial[cedula]["incidencias"]:
        return ""
    data = historial[cedula]
    lines = ["Incidencias anteriores registradas para este cliente:"]
    for i, inc in enumerate(data["incidencias"], 1):
        lines.append(f"  {i}. [{inc['fecha']}] {inc['tipo']} - {inc['descripcion']}")
    lines.append("")
    return "\n".join(lines)


def obtener_historial(chat_id):
    if chat_id not in MEMORIA:
        MEMORIA[chat_id] = []
    return MEMORIA[chat_id]


MAX_TURNOS = 20

def agregar_al_historial(chat_id, rol, mensaje):
    MEMORIA.setdefault(chat_id, [])
    MEMORIA[chat_id].append({"rol": rol, "mensaje": mensaje})
    if len(MEMORIA[chat_id]) > MAX_TURNOS * 2:
        MEMORIA[chat_id] = MEMORIA[chat_id][-(MAX_TURNOS * 2):]


def registrar_metrica(intento, agente, idioma):
    METRICAS["total_conversaciones"] += 1
    if intento in METRICAS["por_intento"]:
        METRICAS["por_intento"][intento] += 1
    if agente in METRICAS["por_agente"]:
        METRICAS["por_agente"][agente] += 1
    if idioma in METRICAS["idiomas"]:
        METRICAS["idiomas"][idioma] += 1


def detectar_sentimiento(texto: str) -> str:
    neg = ["molesto", "queja", "problema", "mal", "error", "cobro", "pesimo", "cancelar", "insatisfecho"]
    pos = ["feliz", "gracias", "bueno", "excelente", "felicitar", "agradecer", "satisfecho"]
    if any(p in texto.lower() for p in neg):
        METRICAS["sentimientos"]["negativo"] += 1
        METRICAS["clientes_insatisfechos"] += 1
        METRICAS["quejas_detectadas"] += 1
        return "negativo"
    if any(p in texto.lower() for p in pos):
        METRICAS["sentimientos"]["positivo"] += 1
        return "positivo"
    METRICAS["sentimientos"]["neutro"] += 1
    return "neutro"


def registrar_problema(tipo_problema):
    if tipo_problema not in METRICAS["problemas_reportados"]:
        METRICAS["problemas_reportados"][tipo_problema] = 0
    METRICAS["problemas_reportados"][tipo_problema] += 1


def generar_reporte():
    agente_info = crear_agente_analitico(None)
    reporte = []
    reporte.append(f"=== {agente_info.role} ===")
    reporte.append(agente_info.backstory)
    reporte.append("")
    reporte.append(f"Total de conversaciones: {METRICAS['total_conversaciones']}")
    reporte.append("")
    reporte.append("Por tipo de interaccion:")
    for k, v in METRICAS["por_intento"].items():
        reporte.append(f"  - {k}: {v}")
    reporte.append("")
    reporte.append("Por agente que respondio:")
    for k, v in METRICAS["por_agente"].items():
        reporte.append(f"  - {k}: {v}")
    reporte.append("")
    reporte.append("Sentimientos detectados:")
    for k, v in METRICAS["sentimientos"].items():
        reporte.append(f"  - {k}: {v}")
    reporte.append("")
    reporte.append(f"Idiomas: Espanol {METRICAS['idiomas']['es']}, Ingles {METRICAS['idiomas']['en']}")
    reporte.append(f"Quejas totales: {METRICAS['quejas_detectadas']}")
    reporte.append(f"Clientes insatisfechos: {METRICAS['clientes_insatisfechos']}")
    reporte.append("")
    if METRICAS["problemas_reportados"]:
        reporte.append("Problemas reportados por tipo:")
        for k, v in sorted(METRICAS["problemas_reportados"].items(), key=lambda x: -x[1]):
            reporte.append(f"  - {k}: {v}")
    reporte.append("")
    return "\n".join(reporte)


def detectar_idioma(texto: str) -> str:
    long_en = 0
    long_es = 0
    for w in texto.lower().split():
        w = w.strip('.,;:!?')
        if w in ("the","is","my","me","you","hello","hi","help","want","need","i","and","to","a","in","this","that","have","not","with","your","for","on","are","can","please","thanks","sorry","what","how","service","change","order","billing"):
            long_en += 1
        elif w in ("hola","el","la","los","las","mi","yo","ayuda","quiero","necesito","gracias","por","favor","este","esta","esto","ese","esa","con","para","por","mas","menos","bien","mal","tengo","puedo","saber","cual","como","donde","cuando","servicio","cambio","orden","factura","que","del","se","no","es","en","lo","le","su","al","tu","un","una"):
            long_es += 1
    return "en" if long_en > long_es else "es"


INSTRUCCION_IDIOMA = {
    "es": "Responde SIEMPRE en espanol. Usa texto plano sin asteriscos ni markdown. Usa guiones (-) para listas.",
    "en": "Responde SIEMPRE in English. Use plain text, no asterisks or markdown. Use dashes (-) for lists."
}


def extraer_cedula(texto: str) -> str | None:
    nums = re.findall(r'\b(\d{7,11})\b', texto)
    return nums[0] if nums else None


def extraer_nombre_completo(texto: str) -> str | None:
    patrones = [
        r'llamo\s+([A-Za-z]+\s+[A-Za-z]+)',
        r'soy\s+([A-Za-z]+\s+[A-Za-z]+)',
        r'nombre\s+(?:es\s+)?([A-Za-z]+\s+[A-Za-z]+)',
    ]
    for p in patrones:
        m = re.search(p, texto.lower())
        if m:
            return m.group(1).title().strip()
    return None


def procesar_mensaje(chat_id: str, mensaje_usuario: str) -> str:
    historial = obtener_historial(chat_id)
    agregar_al_historial(chat_id, "usuario", mensaje_usuario)

    idioma = detectar_idioma(mensaje_usuario)
    lang = INSTRUCCION_IDIOMA[idioma]
    detectar_sentimiento(mensaje_usuario)

    contexto = "\n".join(f"{h['rol']}: {h['mensaje']}" for h in historial[-6:])
    mensaje_completo = f"Historial:\n{contexto}\n\nMensaje del cliente: {mensaje_usuario}"

    cedula = extraer_cedula(mensaje_usuario)
    nombre = extraer_nombre_completo(mensaje_usuario)

    # Paso 1: Verificar identidad si dio cedula + nombre
    if cedula and nombre:
        cliente = buscar_cliente(cedula)
        if cliente and cliente.get("nombre", "").upper() == nombre.upper():
            CLIENTES_VERIFICADOS[chat_id] = {"nombre": cliente["nombre"], "cedula": cliente["cedula"]}
            incidencias_previas = obtener_incidencias_cliente(cedula)
            incidencias_texto = f"\n{incidencias_previas}" if incidencias_previas else ""
            agente_info = crear_agente_verificador(None)
            system_prompt = f"""{agente_info.role}: {agente_info.backstory}

Tu objetivo: {agente_info.goal}

Cliente: {nombre} (cedula {cedula}) - verificado exitosamente.{incidencias_texto}
Instrucciones adicionales:
- Confirma al cliente que esta registrado.
- Si tiene incidencias previas, menciona que ha tenido contacto antes y pregunta si es por el mismo motivo.
- NO muestres datos personales ni detalles de cuentas.
- Pregunta en que puede ayudarle (problema tecnico, facturacion, consulta, etc.).
{lang}"""
            respuesta = ejecutar_llm(system_prompt, mensaje_completo)
            registrar_metrica("consulta", "verificador", idioma)
            agregar_al_historial(chat_id, "asistente", respuesta)
            return respuesta
        elif cliente and cliente.get("nombre", "").upper() != nombre.upper():
            respuesta = f"Lo siento, la cedula {cedula} esta registrada con otro nombre. Verifica tus datos e intenta de nuevo."
            agregar_al_historial(chat_id, "asistente", respuesta)
            return respuesta
        else:
            registrado = registrar_cliente(nombre, cedula)
            if registrado:
                CLIENTES_VERIFICADOS[chat_id] = {"nombre": nombre, "cedula": cedula}
                system_prompt = f"""Eres el Agente de Bienvenida.
El cliente {nombre} (cedula {cedula}) acaba de ser registrado en el sistema como nuevo cliente.
INSTRUCCIONES:
- Dale la bienvenida como nuevo cliente.
- Pregunta en que puede ayudarle (problema tecnico, facturacion, consulta, contratar, etc.).
- {lang}"""
                respuesta = ejecutar_llm(system_prompt, mensaje_completo)
                registrar_metrica("consulta", "verificador", idioma)
                agregar_al_historial(chat_id, "asistente", respuesta)
                return respuesta
            else:
                respuesta = f"Lo siento, no se pudo registrar. La cedula {cedula} ya existe en el sistema."
                agregar_al_historial(chat_id, "asistente", respuesta)
                return respuesta

    # Paso 2: Si ya esta verificado, detectar problema
    if chat_id in CLIENTES_VERIFICADOS:
        problema = buscar_termino_en_problemas(mensaje_usuario)
        intento = clasificar_intento(mensaje_usuario, historial)

        if problema:
            id_asignado = problema["id_request"]
            tipo = problema["tipo"]
            desc = problema["descripcion"]
            registrar_problema(tipo)

            cedula_cli = CLIENTES_VERIFICADOS[chat_id]["cedula"]
            nombre_cli = CLIENTES_VERIFICADOS[chat_id]["nombre"]
            registrar_incidencia_cliente(cedula_cli, nombre_cli, tipo, desc, mensaje_usuario)
            incidencias_previas = obtener_incidencias_cliente(cedula_cli)
            incidencias_texto = f"\n{incidencias_previas}" if incidencias_previas else ""

            if intento == "queja" or problema["sentimiento_esperado"] == "negativo":
                nombre_agente = "retencion"
                agente_info = crear_agente_retencion(None)
                system_prompt = f"""{agente_info.role}: {agente_info.backstory}

Tu objetivo: {agente_info.goal}

Cliente: {nombre_cli}
Problema detectado: {tipo} - {desc}
Se ha generado el siguiente caso de seguimiento: {id_asignado}
{incidencias_texto}
El cliente esta molesto. Ofrece una solucion empatica. Si tiene incidencias previas similares, reconocelo y ofrece una solucion mas solida.
{lang}"""
                respuesta = ejecutar_llm(system_prompt, mensaje_completo)
                registrar_metrica("queja", "retencion", idioma)
                agregar_al_historial(chat_id, "asistente", respuesta)
                return respuesta
            else:
                nombre_agente = "consulta"
                agente_info = crear_agente_consulta(None)
                system_prompt = f"""{agente_info.role}: {agente_info.backstory}

Tu objetivo: {agente_info.goal}

Cliente: {nombre_cli}
Caso asignado: {id_asignado} - {tipo}
Descripcion del caso: {desc}
{incidencias_texto}
Responde al cliente indicando que ha entendido su solicitud y
proporciona informacion util segun el tipo de caso detectado.
Si tiene incidencias previas relacionadas, haz referencia a ellas.
{lang}"""
                respuesta = ejecutar_llm(system_prompt, mensaje_completo)
                registrar_metrica("consulta", "consulta", idioma)
                agregar_al_historial(chat_id, "asistente", respuesta)
                return respuesta

        # Si no se detecto problema especifico, derivar a consulta general
        nombre_agente = "consulta"
        cedula_cli = CLIENTES_VERIFICADOS[chat_id]["cedula"]
        nombre_cli = CLIENTES_VERIFICADOS[chat_id]["nombre"]
        incidencias_previas = obtener_incidencias_cliente(cedula_cli)
        incidencias_texto = f"\n{incidencias_previas}" if incidencias_previas else ""
        agente_info = crear_agente_consulta(None)
        system_prompt = f"""{agente_info.role}: {agente_info.backstory}

Tu objetivo: {agente_info.goal}

Cliente verificado: {nombre_cli}
{incidencias_texto}
El cliente no ha especificado claramente su problema.
Si tiene incidencias previas, preguntale si es por el mismo motivo.
Ayudale a identificar que tipo de situacion tiene preguntando:
- Problemas con internet o equipo?
- Problemas de facturacion?
- Consulta de saldo o informacion?
- Desea contratar o cancelar?
{lang}"""
        respuesta = ejecutar_llm(system_prompt, mensaje_completo)
        registrar_metrica("consulta", "consulta", idioma)
        agregar_al_historial(chat_id, "asistente", respuesta)
        return respuesta

    # Paso 3: Si no esta verificado y no dio datos, clasificar
    intento = clasificar_intento(mensaje_usuario, historial)
    nombre_agente = intento

    if intento == "despedida":
        respuesta_es = "Gracias a ti por contactarnos. Que tengas un excelente dia. Si necesitas algo mas, aqui estaremos."
        respuesta_en = "Thank you for contacting us. Have a great day. If you need anything else, we'll be here."
        respuesta = respuesta_es if idioma == "es" else respuesta_en
        agregar_al_historial(chat_id, "asistente", respuesta)
        return respuesta
    elif intento == "saludo":
        agente_info = crear_agente_saludo(None)
        system_prompt = f"""{agente_info.role}: {agente_info.backstory}

Tu objetivo: {agente_info.goal}

{lang}"""
        respuesta = ejecutar_llm(system_prompt, mensaje_completo)
    elif intento == "queja":
        nombre_agente = "retencion"
        agente_info = crear_agente_retencion(None)
        system_prompt = f"""{agente_info.role}: {agente_info.backstory}

Tu objetivo: {agente_info.goal}

El cliente esta molesto pero no esta verificado. Pide amablemente que se identifique
con su nombre completo y su numero de cedula (SOLO numeros, sin puntos, sin espacios).
{lang}"""
        respuesta = ejecutar_llm(system_prompt, mensaje_completo)
    else:
        nombre_agente = "consulta"
        agente_info = crear_agente_consulta(None)
        system_prompt = f"""{agente_info.role}: {agente_info.backstory}

Tu objetivo: {agente_info.goal}

El cliente no esta verificado. Pide amablemente que proporcione su nombre
completo y su numero de cedula (SOLO numeros, sin puntos, sin espacios)
para poder identificarle y ayudarle.
{lang}"""
        respuesta = ejecutar_llm(system_prompt, mensaje_completo)

    registrar_metrica(intento, nombre_agente, idioma)
    agregar_al_historial(chat_id, "asistente", respuesta)
    return respuesta


def clasificar_intento(mensaje: str, historial: list) -> str:
    msg_lower = mensaje.lower()

    despedida = ["gracias", "adios", "chao", "bye", "goodbye", "thank you",
                 "thanks", "hasta luego", "nos vemos", "que tengas buen",
                 "que tenga buen", "buena noche"]
    if historial and any(d in msg_lower for d in despedida):
        return "despedida"
    if historial and msg_lower.strip() in ("gracias", "bye", "adios", "chao", "thanks"):
        return "despedida"

    saludos = ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "hello", "hi"]
    if any(s in msg_lower for s in saludos) and len(historial) == 0:
        return "saludo"

    queja = ["molesto", "queja", "problema", "mal servicio", "insatisfecho",
             "error", "cobro", "pesimo", "no funciona", "cancelar", "mad",
             "angry", "upset", "complaint", "bad service"]
    if any(p in msg_lower for p in queja):
        return "queja"

    if historial:
        return "consulta"
    return "saludo"


def ejecutar_llm(system_prompt: str, user_message: str) -> str:
    try:
        respuesta = cliente_groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=500,
            timeout=30,
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error en llamada a Groq LLM: {e}")
        raise RuntimeError(f"Error al generar respuesta. Intenta de nuevo.") from e