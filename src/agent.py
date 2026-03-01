from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()
from typing import TypedDict, Annotated, Literal
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import operator
from src.rag import query_rag

# Definición de estructuras de datos para las alertas y los tickets.

class ZabbixAlert(BaseModel):
    alert_id: str = Field(..., description="ID único de la alerta")
    server_id: str = Field(..., description="IP o hostname del servidor")
    data: str = Field(..., description="Descripción técnica del error")
    urgency_level: int = Field(..., ge=1, le=5)

class ServerInfo(BaseModel):
    cpu_usage: float
    memory_usage: float
    location: str
    state: str
    os: str = "Ubuntu 22.04"

class EasyVistaTicket(BaseModel):
    title: str = Field(..., description="Título corto del incidente")
    summary: str = Field(..., description="Resumen del problema y el servidor afectado")
    details: str = Field(..., description="Pasos de resolución extraídos de logs o bookstack")
    priority: int = Field(..., description="Prioridad del 1 al 5")

# Estructura para que el LLM decida el siguiente paso en el flujo
class RouterDecision(BaseModel):
    next_action: Literal["logs_db", "rag_bookstack"] = Field(
        ..., 
        description="Si el error es conocido por historial, usa 'logs_db'. Si requiere consultar manuales de arquitectura, usa 'rag_bookstack'."
    )
    category: Literal["security", "network", "hardware", "general"] = Field(
        "general",
        description="Categoría técnica de la alerta para filtrar la búsqueda"
    )
    reasoning: str = Field(..., description="Breve justificación de la decisión")

# Estado compartido a lo largo del grafo
class MessageState(TypedDict):
    zabbix_alert: ZabbixAlert
    server_info: ServerInfo
    router_decision: RouterDecision
    retrieved_knowledge: str
    easyvista_ticket: EasyVistaTicket
    messages: Annotated[list, operator.add]

llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)

async def call_phpipam(state: MessageState) -> dict:
    """Enriquece la alerta con información del servidor simulando una consulta a un IPAM."""
    print(f"-> Ejecutando: call_phpipam para servidor {state['zabbix_alert'].server_id}")
    
    server_db = {
        "production-web-01": {"location": "Madrid - Rack 04", "os": "Ubuntu 22.04", "state": "Critical"},
        "core-db-02": {"location": "Barcelona - Rack 02", "os": "RedHat 9", "state": "Warning"},
        "backup-01": {"location": "Lisboa - Rack 01", "os": "CentOS 7", "state": "Active"}
    }
    
    server_id = state["zabbix_alert"].server_id
    info = server_db.get(server_id, {"location": "Desconocido", "os": "Linux Genérico", "state": "Unknown"})
    
    return {"server_info": ServerInfo(
        cpu_usage=95.5,
        memory_usage=88.0,
        location=info["location"],
        state=info["state"],
        os=info["os"]
    )}

async def router_retriever(state: MessageState) -> dict:
    """Analiza la alerta y decide si buscar en logs históricos o manuales técnicos."""
    print("-> Ejecutando: router_retriever")
    alert = state["zabbix_alert"]
    
    structured_llm = llm.with_structured_output(RouterDecision)
    
    prompt = f"""
    Eres un ingeniero SRE experto. Analiza esta alerta de Zabbix:
    Error: {alert.data}
    Urgencia (1-5): {alert.urgency_level}
    
    Decide si buscar la solución en el historial de Logs de este servidor (logs_db) 
    o consultar los manuales oficiales de arquitectura (rag_bookstack).
    
    También identifica si la categoría es 'security', 'network', 'hardware' o 'general'.
    """
    
    decision = await structured_llm.ainvoke(prompt)
    print(f"   [Decisión]: Ir a {decision.next_action} (Categoría: {decision.category}). Razón: {decision.reasoning}")
    return {"router_decision": decision}

async def node_logs_db(state: MessageState) -> dict:
    """Simula una consulta asíncrona a una base de datos de logs pasados."""
    print("-> Ejecutando: logs_db")
    alert_data = state["zabbix_alert"].data.lower()
    if "cpu" in alert_data:
        knowledge = "LOGS HISTÓRICOS: Se detectó un patrón recurrente de picos de CPU por el proceso 'php-fpm'. La solución aplicada anteriormente fue aumentar el pm.max_children."
    elif "disk" in alert_data:
        knowledge = "LOGS HISTÓRICOS: Disco lleno en /var/log. Se ejecutó purga de logs antiguos."
    else:
        knowledge = "LOGS HISTÓRICOS: No se encontraron entradas exactas, pero fallos similares se resolvieron reiniciando el servicio afectado."
        
    return {"retrieved_knowledge": knowledge}

async def node_rag_bookstack(state: MessageState) -> dict:
    """Realiza una búsqueda semántica en la base de conocimientos RAG."""
    print("-> Ejecutando: rag_bookstack")
    query = state["zabbix_alert"].data
    category = state["router_decision"].category
    
    # Ajuste de categorías para coincidir con la base de datos de documentos
    filter_cat = None
    if category != "general":
        filter_cat = "NETWORKING" if category == "network" else category.upper()
    
    knowledge = await query_rag(query, category=filter_cat)
    
    if not knowledge:
        knowledge = "No se encontró información relevante en los manuales de BookStack."
        
    return {"retrieved_knowledge": knowledge}

async def create_easyvista_ticket(state: MessageState) -> dict:
    """Genera un ticket de incidencias unificando el contexto y la solución."""
    print("-> Ejecutando: create_easyvista_ticket")
    
    structured_llm = llm.with_structured_output(EasyVistaTicket)
    
    prompt = f"""
    Crea un ticket para EasyVista con la siguiente información:
    Servidor Afectado: {state['zabbix_alert'].server_id} (Ubicación: {state['server_info'].location}, OS: {state['server_info'].os})
    Problema detectado por Zabbix: {state['zabbix_alert'].data}
    
    Solución técnica recomendada obtenida de nuestra base de datos:
    {state['retrieved_knowledge']}
    
    Asegúrate de que el ticket tenga un título claro y la prioridad adecuada (basada en la urgencia {state['zabbix_alert'].urgency_level}).
    """
    
    ticket = await structured_llm.ainvoke(prompt)
    return {"easyvista_ticket": ticket}

def route_after_router(state: MessageState) -> str:
    """Determina la transición basada en la decisión del router."""
    return state["router_decision"].next_action

def create_graph_agent():
    """Construye y conecta el grafo de LangGraph."""
    workflow = StateGraph(MessageState)
    
    workflow.add_node("call_phpipam", call_phpipam)
    workflow.add_node("router_retriever", router_retriever)
    workflow.add_node("logs_db", node_logs_db)
    workflow.add_node("rag_bookstack", node_rag_bookstack)
    workflow.add_node("create_easyvista_ticket", create_easyvista_ticket)
    
    workflow.set_entry_point("call_phpipam")
    workflow.add_edge("call_phpipam", "router_retriever")
    
    workflow.add_conditional_edges(
        "router_retriever",
        route_after_router,
        {
            "logs_db": "logs_db",
            "rag_bookstack": "rag_bookstack"
        }
    )
    
    workflow.add_edge("logs_db", "create_easyvista_ticket")
    workflow.add_edge("rag_bookstack", "create_easyvista_ticket")
    workflow.add_edge("create_easyvista_ticket", END)
    
    return workflow

if __name__ == "__main__":
    agent = create_graph_agent().compile()
    # create a picture of the graph for visualization (optional)
    print(agent.get_graph().draw_mermaid())
