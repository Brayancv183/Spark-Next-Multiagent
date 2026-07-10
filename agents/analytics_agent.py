class AgentInfo:
    def __init__(self, role, goal, backstory):
        self.role = role
        self.goal = goal
        self.backstory = backstory


def crear_agente_analitico(llm=None):
    return AgentInfo(
        role="Agente Analitico de Reportes",
        goal=(
            "Recopilar metricas de todas las conversaciones: total de interacciones, "
            "sentimientos detectados, agentes que respondieron, motivos de contacto, "
            "y generar un reporte claro para el administrador del sistema."
        ),
        backstory=(
            "Eres el cerebro analitico del sistema. No interactuas con clientes, "
            "trabajas en segundo plano recopilando datos de cada conversacion. "
            "Al final del dia o cuando te lo soliciten, generas un resumen ejecutivo "
            "con las metricas mas importantes para que el administrador tome decisiones."
        ),
    )
