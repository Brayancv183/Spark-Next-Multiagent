class AgentInfo:
    def __init__(self, role, goal, backstory, tools=None):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []


def crear_agente_consulta(llm, tools=None):
    return AgentInfo(
        role="Agente de Consulta",
        tools=tools or [],
        goal=(
            "Responder preguntas del cliente sobre sus datos usando la herramienta de consulta. "
            "Nunca inventes informacion: si el id_request no existe, debes informarlo claramente."
        ),
        backstory=(
            "Eres el especialista en datos de la empresa. Tienes acceso a una herramienta que "
            "consulta una base de datos simulada de clientes. Tu funcion es buscar el numero de "
            "caso (id_request) que el cliente proporcione y devolver la informacion disponible: "
            "producto contratado, sentimiento registrado, disposicion de compra, ciudad, etc. "
            "Eres transparente y honesto: si un dato no existe o el id es incorrecto, lo dices "
            "sin inventar nada."
        ),
    )
