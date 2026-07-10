import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Limpiar datos de pruebas anteriores
data_file = os.path.join(os.path.dirname(__file__), "..", "data", "historial_clientes.json")
if os.path.exists(data_file):
    os.remove(data_file)

from tools.client_lookup_tool import buscar_cliente, registrar_cliente, buscar_termino_en_problemas
from crew import (
    registrar_incidencia_cliente, cargar_historial_clientes,
    obtener_incidencias_cliente, clasificar_intento,
    extraer_nombre_completo, extraer_cedula,
    detectar_idioma, detectar_sentimiento, METRICAS
)

ok = 0
fail = 0

def check(nombre, resultado, esperado):
    global ok, fail
    if resultado == esperado:
        ok += 1
        print(f"  [OK] {nombre}")
    else:
        fail += 1
        print(f"  [FAIL] {nombre}: esperado {esperado!r}, obtuve {resultado!r}")

print("=== registrar_cliente - nuevo usuario ===")
buscar_cliente("9988776655")  # limpia cache
r = buscar_cliente("9988776655")
check("no existe antes", r, None)
r = registrar_cliente("Juan Perez", "9988776655")
check("registro exitoso", r, True)
r = buscar_cliente("9988776655")
check("existe despues", r["nombre"], "Juan Perez")

print("\n=== registrar_cliente - duplicado ===")
r = registrar_cliente("Juan Perez", "9988776655")
check("no sobrescribe", r, False)

print("\n=== registrar_incidencia_cliente ===")
registrar_incidencia_cliente("9988776655", "Juan Perez", "problema_tecnico", "Internet no funciona", "Estoy molesto")
registrar_incidencia_cliente("9988776655", "Juan Perez", "problema_facturacion", "Cobro indebido", "Me cobraron de mas")
data = cargar_historial_clientes()
juan = data.get("9988776655", {})
check("cliente en historial", juan["nombre"], "Juan Perez")
check("2 incidencias", len(juan["incidencias"]), 2)
check("tipo 1", juan["incidencias"][0]["tipo"], "problema_tecnico")
check("tipo 2", juan["incidencias"][1]["tipo"], "problema_facturacion")

print("\n=== obtener_incidencias_cliente ===")
txt = obtener_incidencias_cliente("9988776655")
check("tiene historial", "Incidencias anteriores" in txt, True)
check("menciona tipo", "problema_tecnico" in txt, True)
txt2 = obtener_incidencias_cliente("0000000000")
check("sin historial", txt2, "")

print("\n=== clasificar_intento ===")
h = [{"rol": "usuario", "mensaje": "hola"}]
check('despedida "gracias"', clasificar_intento("gracias", h), "despedida")
check('despedida "adios"', clasificar_intento("adios", h), "despedida")
check('despedida "bye"', clasificar_intento("bye bye", h), "despedida")
check('despedida "gracias, buen dia"', clasificar_intento("gracias, que tengas buen dia", h), "despedida")
check('saludo sin historial', clasificar_intento("hola", []), "saludo")
check('queja', clasificar_intento("estoy molesto", h), "queja")

print("\n=== extraer_nombre_completo ===")
check('"me llamo X"', extraer_nombre_completo("Me llamo Carlos Munoz"), "Carlos Munoz")
check('"soy X"', extraer_nombre_completo("Soy Maria Rodriguez"), "Maria Rodriguez")
check('"nombre es X"', extraer_nombre_completo("Mi nombre es Pedro Gomez"), "Pedro Gomez")
check('sin nombre', extraer_nombre_completo("Hola buenos dias"), None)

print("\n=== extraer_cedula ===")
check('cedula 1012345678', extraer_cedula("Mi cedula es 1012345678"), "1012345678")
check('sin cedula', extraer_cedula("Hola buenos dias"), None)

print("\n=== detectar_idioma ===")
check('espanol', detectar_idioma("Hola buenos dias"), "es")
check('ingles', detectar_idioma("Hello good morning"), "en")

print("\n=== detectar_sentimiento ===")
METRICAS["sentimientos"] = {"positivo": 0, "neutro": 0, "negativo": 0}
METRICAS["clientes_insatisfechos"] = 0
METRICAS["quejas_detectadas"] = 0
check('negativo', detectar_sentimiento("Estoy muy molesto"), "negativo")
check('positivo', detectar_sentimiento("Excelente servicio gracias"), "positivo")
check('neutro', detectar_sentimiento("Quiero saber mi saldo"), "neutro")

print("\n=== buscar_termino_en_problemas ===")
r = buscar_termino_en_problemas("el internet no funciona")
check('internet', r["tipo"] if r else None, "problema_tecnico")
r = buscar_termino_en_problemas("me cobraron de mas")
check('cobro', r["tipo"] if r else None, "problema_facturacion")
r = buscar_termino_en_problemas("quiero saber mi saldo")
check('saldo', r["tipo"] if r else None, "consulta_saldo")
r = buscar_termino_en_problemas("hola buenos dias")
check('sin match', r, None)

# Limpiar datos de prueba para no contaminar ejecuciones futuras
data_file_clientes = os.path.join(os.path.dirname(__file__), "..", "data", "clientes.json")
with open(data_file_clientes, "r", encoding="utf-8") as f:
    clientes = json.load(f)
clientes = [c for c in clientes if int(c["cedula"]) < 9000000000]
with open(data_file_clientes, "w", encoding="utf-8") as f:
    json.dump(clientes, f, ensure_ascii=False, indent=2)

print(f"\n======== RESULTADOS: {ok} OK, {fail} FAIL ========")
sys.exit(0 if fail == 0 else 1)
