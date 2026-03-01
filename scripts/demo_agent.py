import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.agent import create_graph_agent, ZabbixAlert
import json

def test_hardware_alert():
    print("=== Test de alerta de Hardware (RAG esperado) ===")
    agent = create_graph_agent().compile()
    
    alert = ZabbixAlert(
        alert_id="ZB-999",
        server_id="production-web-01",
        data="SSD S.M.A.R.T. Failure Prediction on /dev/sda",
        urgency_level=4
    )
    
    result = agent.invoke({"zabbix_alert": alert})
    print("Ticket generado:")
    print(json.dumps(result["easyvista_ticket"].model_dump(), indent=2))

def test_logs_alert():
    print("=== Test de alerta recurrente de CPU (Búsqueda en Logs esperada) ===")
    agent = create_graph_agent().compile()
    
    alert = ZabbixAlert(
        alert_id="ZB-100",
        server_id="core-db-02",
        data="High CPU usage on production-web-01",
        urgency_level=3
    )
    
    result = agent.invoke({"zabbix_alert": alert})
    print("Ticket generado:")
    print(json.dumps(result["easyvista_ticket"].model_dump(), indent=2))

if __name__ == "__main__":
    test_hardware_alert()
    test_logs_alert()
