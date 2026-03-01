from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
import operator


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

class EasyVistaTicket(BaseModel):
    title: str
    summary: str
    details: str
    priority: int

class MessageState(TypedDict):
    zabbix_alert: ZabbixAlert
    server_info: ServerInfo
    easyvista_ticket: EasyVistaTicket
    messages: Annotated[str, operator.add ]

def get_zabbix_data(state: MessageState) -> ServerInfo:
    """Get server information from Zabbix based on the alert data."""
    # Simulate fetching data from Zabbix
    #request using PhpIPAM to get the server information based on the host_ip
    host_ip = state["zabbix_alert"].server_id
    # response = request.post(hostip)
    #datos_json = response.json()
    #server_info = ServerInfo(**datos_json)
    return {"server_info":ServerInfo(
        cpu_usage=75.5,
        memory_usage=60.0,
        location="Datacenter A",
        state="Running"
    )}

llm = init_chat_model(model="gemini-flash-latest", model_provider="google_genai")
llm_with_structure = llm.with_structured_output(schema=EasyVistaTicket)

def create_easyvista_ticket(state : MessageState) -> str:
    """Creates an EasyVista ticket and creates it via API."""
    #llm call to generate the ticket details based on the summary and details provided
    server_info = state["server_info"]
    ticket = llm_with_structure.invoke(input=server_info)
    # response = requests.post("https://easyvista.wehunt.com/api/v1/incidents", json=ticket.dict())

    return {"easyvista_ticket" : ticket}



def create_graph_agent():
    workflow = StateGraph(state_schema=MessageState)
    workflow.add_node(node="get_zabbix_data", action=get_zabbix_data)
    workflow.add_node(node="create_easyvista_ticket", action=create_easyvista_ticket)
    workflow.set_entry_point("get_zabbix_data")
    workflow.set_finish_point("create_easyvista_ticket")
    workflow.add_edge('get_zabbix_data', "create_easyvista_ticket")
    return workflow

