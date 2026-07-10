import json
import os
import functools

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@functools.lru_cache(maxsize=4)
def _load_json(filename):
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def _invalidar_cache():
    _load_json.cache_clear()


def buscar_cliente(cedula):
    clientes = _load_json("clientes.json")
    for c in clientes:
        if c["cedula"] == cedula:
            return c
    return None


def registrar_cliente(nombre, cedula):
    path = os.path.join(DATA_DIR, "clientes.json")
    clientes = _load_json("clientes.json")
    for c in clientes:
        if c["cedula"] == cedula:
            return False
    clientes.append({"nombre": nombre, "cedula": cedula})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clientes, f, ensure_ascii=False, indent=2)
    _invalidar_cache()
    return True


def buscar_problema(termino):
    termino = termino.strip().upper()
    problemas = _load_json("problemas.json")
    for p in problemas:
        if p["id_request"] == termino:
            return p
        if p["tipo"] == termino:
            return p
    return None


def buscar_termino_en_problemas(texto):
    texto_lower = texto.lower()
    problemas = _load_json("problemas.json")
    for p in problemas:
        tipo = p["tipo"].replace("_", " ")
        if tipo in texto_lower:
            return p
    keywords = {
        "internet": "problema_tecnico", "no funciona": "problema_tecnico", "corte": "problema_tecnico", "senal": "problema_tecnico",
        "factura": "problema_facturacion", "cobro": "problema_facturacion", "cobr": "problema_facturacion", "pago": "problema_facturacion",
        "saldo": "consulta_saldo", "cuenta": "consulta_saldo",
        "felicitar": "felicitacion_upgrade", "upgrade": "felicitacion_upgrade", "mejorar": "felicitacion_upgrade",
        "cancelar": "cancelacion", "cancelacion": "cancelacion",
        "contratar": "nueva_contratacion", "nuevo servicio": "nueva_contratacion",
        "modem": "problema_equipo", "router": "problema_equipo", "equipo": "problema_equipo",
        "cambiar plan": "cambio_plan", "plan mas": "cambio_plan",
        "queja": "queja_atencion", "asesor": "queja_atencion", "atencion": "queja_atencion",
        "cobertura": "consulta_cobertura",
        "actualizar": "actualizacion_datos", "direccion": "actualizacion_datos",
        "promocion": "promociones", "oferta": "promociones", "descuento": "promociones",
        "velocidad": "problema_velocidad", "lento": "problema_velocidad"
    }
    for word, tipo in keywords.items():
        if word in texto_lower:
            for p in problemas:
                if p["tipo"] == tipo:
                    return p
    return None