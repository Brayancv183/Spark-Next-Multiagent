import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY no definida"); sys.exit(1)

from crew import procesar_mensaje, MEMORIA, METRICAS, generar_reporte, CLIENTES_VERIFICADOS

CHAT = "demo_001"

def p(n, msg, resp):
    print(f"\n{'='*60}")
    print(f"  PASO {n}: {msg}")
    print(f"{'='*60}")
    print(f"  Tu: {msg}")
    print(f"  Bot: {resp[:300] if len(resp)>300 else resp}")
    input("  [Enter para siguiente paso] ")

def llamar(msg):
    try:
        return procesar_mensaje(CHAT, msg)
    except Exception as e:
        return f"[Error controlado: {e}]"

# Reset state
MEMORIA.pop(CHAT, None)
CLIENTES_VERIFICADOS.pop(CHAT, None)
print("Estado limpio. Iniciando demo...")
input("[Enter para empezar] ")

p(1, "Hola buenos dias", llamar("Hola buenos dias"))
p(2, "Me llamo Carlos Munoz y mi cedula es 1012345678", llamar("Me llamo Carlos Munoz y mi cedula es 1012345678"))
p(3, "Quiero saber mi saldo", llamar("Quiero saber mi saldo"))
p(4, "Estoy muy molesto, el internet no funciona", llamar("Estoy muy molesto, el internet no funciona"))
p(5, "Gracias, que tengas buen dia", llamar("Gracias, que tengas buen dia"))

# Nuevo cliente
MEMORIA.pop(CHAT, None)
CLIENTES_VERIFICADOS.pop(CHAT, None)
print("\n--- Nuevo cliente ---")
input("[Enter] ")

p(6, "Hola soy Laura Castro y mi cedula es 9988770011", llamar("Hola soy Laura Castro y mi cedula es 9988770011"))

print("\n" + "="*60)
print("  REPORTE FINAL")
print("="*60)
print(generar_reporte())
print("\nDemo completa!")
