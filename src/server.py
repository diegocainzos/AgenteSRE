from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from langgraph.graph.state import CompiledStateGraph
from fastapi import FastAPI, HTTPException, Depends, Request
from src.agent import ZabbixAlert, create_graph_agent
import uuid

async def lifespan(app: FastAPI):
    # Compilamos el agente LangGraph para tenerlo listo en el estado de la app de FastAPI
    workflow = create_graph_agent()
    app.state.agent = workflow.compile()
    
    print("🚀 Grafo de LangGraph compilado y listo.")
    yield
    print("🛑 Apagando recursos...")

app = FastAPI(lifespan=lifespan)

def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.agent

@app.post("/webhook")
async def webhook(zabbix_alert: ZabbixAlert, graph: CompiledStateGraph = Depends(get_graph)):
    response = await graph.ainvoke({"zabbix_alert": zabbix_alert})

    return {"easyvista_ticket": response["easyvista_ticket"]}