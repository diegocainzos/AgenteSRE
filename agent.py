from langchain_google_genai import ChatGoogleGenerativeAI # Usa la librería correcta para Gemini
from langchain_core.prompts import PromptTemplate
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import operator

# --- 1. MODELOS DE DATOS (PYDANTIC) ---

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
    os: str = "Ubuntu 22.04" # Añadido para dar contexto

class EasyVistaTicket(BaseModel):
    title: str = Field(..., description="Título corto del incidente")
    summary: str = Field(..., description="Resumen del problema y el servidor afectado")
    details: str = Field(..., description="Pasos de resolución extraídos de logs o bookstack")
    priority: int = Field(..., description="Prioridad del 1 al 5")

# Modelo que usará el Router para decidir
class RouterDecision(BaseModel):
    next_action: Literal["logs_db", "rag_bookstack"] = Field(
        ..., 
        description="Si la urgencia es baja (1-2) o es un problema recurrente, usa 'logs_db'. Si es urgencia alta (3-5) o un error de sistema crítico, usa 'rag_bookstack'."
    )
    reasoning: str = Field(..., description="Breve justificación de la decisión")

# --- 2. ESTADO DEL GRAFO ---

class MessageState(TypedDict):
    zabbix_alert: ZabbixAlert
    server_info: ServerInfo
    router_decision: RouterDecision
    retrieved_knowledge: str # Aquí guardaremos lo que encontremos en Logs o BookStack
    easyvista_ticket: EasyVistaTicket
    messages: Annotated[list, operator.add] # Mejor como lista para el historial

# --- 3. CONFIGURACIÓN DEL LLM ---
llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)

# --- 4. NODOS DEL GRAFO ---

def call_phpipam(state: MessageState) -> dict:
    """Nodo 1: Enriquecimiento de datos (Mock de PhpIPAM)"""
    print("-> Ejecutando: call_phpipam")
    return {"server_info": ServerInfo(
        cpu_usage=95.5,
        memory_usage=88.0,
        location="Datacenter Madrid - Rack 04",
        state="Critical",
        os="Linux RedHat"
    )}

def router_retriever(state: MessageState) -> dict:
    """Nodo 2: El Cerebro que decide a qué DB consultar"""
    print("-> Ejecutando: router_retriever")
    alert = state["zabbix_alert"]
    
    # Forzamos al LLM a devolver la estructura Pydantic de la decisión
    structured_llm = llm.with_structured_output(RouterDecision)
    
    prompt = f"""
    Eres un ingeniero SRE experto. Analiza esta alerta de Zabbix:
    Error: {alert.data}
    Urgencia (1-5): {alert.urgency_level}
    
    Decide si buscar la solución en el historial de Logs de este servidor (logs_db) 
    o consultar los manuales oficiales de arquitectura (rag_bookstack).
    """
    
    decision = structured_llm.invoke(prompt)
    print(f"   [Decisión]: Ir a {decision.next_action}. Razón: {decision.reasoning}")
    return {"router_decision": decision}

def node_logs_db(state: MessageState) -> dict:
    """Nodo 3A: Simula la búsqueda en logs históricos"""
    print("-> Ejecutando: logs_db")
    # En un caso real, harías una query SQL o Elasticsearch aquí
    knowledge = "LOGS HISTÓRICOS: Este error ocurrió hace 3 semanas. La solución fue reiniciar el servicio 'systemd-journald'."
    return {"retrieved_knowledge": knowledge}

def node_rag_bookstack(state: MessageState) -> dict:
    """Nodo 3B: Simula el RAG-Fusion buscando en manuales"""
    print("-> Ejecutando: rag_fusion_bookstack")
    # En un caso real, aquí iría tu ChromaDB/FAISS Retriever
    knowledge = "MANUAL BOOKSTACK (SOP-402): Para errores críticos de CPU en RedHat, proceda a aislar el nodo del balanceador y haga un dump de memoria antes de reiniciar."
    return {"retrieved_knowledge": knowledge}

def create_easyvista_ticket(state: MessageState) -> dict:
    """Nodo 4: Crea el ticket final uniendo el contexto y la solución"""
    print("-> Ejecutando: create_easyvista_ticket")
    
    structured_llm = llm.with_structured_output(EasyVistaTicket)
    
    prompt = f"""
    Crea un ticket para EasyVista con la siguiente información:
    Servidor Afectado: {state['zabbix_alert'].server_id} (Ubicación: {state['server_info'].location})
    Problema detectado por Zabbix: {state['zabbix_alert'].data}
    
    Solución técnica recomendada obtenida de nuestra base de datos:
    {state['retrieved_knowledge']}
    
    Asegúrate de que el ticket tenga un título claro y la prioridad adecuada.
    """
    
    ticket = structured_llm.invoke(prompt)
    return {"easyvista_ticket": ticket}

# --- 5. LÓGICA CONDICIONAL (CONDITIONAL EDGE) ---

def route_after_router(state: MessageState) -> str:
    """Lee el estado y devuelve el nombre del siguiente nodo"""
    decision = state["router_decision"].next_action
    if decision == "logs_db":
        return "logs_db"
    else:
        return "rag_bookstack"

# --- 6. CONSTRUCCIÓN DEL GRAFO ---

def create_graph_agent():
    workflow = StateGraph(MessageState)
    
    # Añadimos los nodos
    workflow.add_node("call_phpipam", call_phpipam)
    workflow.add_node("router_retriever", router_retriever)
    workflow.add_node("logs_db", node_logs_db)
    workflow.add_node("rag_bookstack", node_rag_bookstack)
    workflow.add_node("create_easyvista_ticket", create_easyvista_ticket)
    
    # Definimos el flujo
    workflow.set_entry_point("call_phpipam")
    workflow.add_edge("call_phpipam", "router_retriever")
    
    # CONDITIONAL EDGE: Del router nos dividimos en dos caminos posibles
    workflow.add_conditional_edges(
        "router_retriever",
        route_after_router,
        {
            "logs_db": "logs_db",
            "rag_bookstack": "rag_bookstack"
        }
    )
    
    # Ambos caminos terminan en la creación del ticket
    workflow.add_edge("logs_db", "create_easyvista_ticket")
    workflow.add_edge("rag_bookstack", "create_easyvista_ticket")
    
    # Finalizamos
    workflow.add_edge("create_easyvista_ticket", END)
    
    return workflow