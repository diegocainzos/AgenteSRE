from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from langgraph.graph.state import CompiledStateGraph
from fastapi import FastAPI, HTTPException, Depends, Request
from agent import ZabbixAlert, create_graph_agent
import uuid

# Generate a random UUID (version 4)
async def lifespan(app: FastAPI):
    # 1. Configuramos la persistencia (Checkpointer)
    # Si usas Postgres, aquí abrirías la conexión

    # 2. Compilamos el grafo con sus dependencias
    workflow = create_graph_agent()
    app.state.agent = workflow.compile()
    
    print("🚀 Grafo de LangGraph compilado y listo.")
    yield
    print("🛑 Apagando recursos...")

app = FastAPI(lifespan=lifespan)

@app.get("/{alert_id}")
def test_endpoint(alert_id: str):
    if True == True:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"message": f"Processing alert with ID: {alert_id}"}

def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.agent

# @app.post("/process_alert/")
# def process_alert(alert: ZabbixAlert):
#     server_info = get_zabbix_data(alert)
#     ticket_response = create_easyvista_ticket(server_info)
#     return {"message": ticket_response}
random_uuid = uuid.uuid4()

@app.post("/webhook")
def webhook(zabbix_alert: ZabbixAlert, graph: CompiledStateGraph = Depends(get_graph)):
    response = graph.invoke({"zabbix_alert": zabbix_alert})

    return {"easyvista_ticket": response["easyvista_ticket"]}