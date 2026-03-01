import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_webhook_hardware():
    print("--- Enviando alerta de Hardware ---")
    payload = {
        "alert_id": "ZB-999",
        "server_id": "production-web-01",
        "data": "SSD S.M.A.R.T. Failure Prediction on /dev/sda",
        "urgency_level": 4
    }
    response = requests.post(f"{BASE_URL}/webhook", json=payload)
    print(f"Estado: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def test_webhook_network():
    print("--- Enviando alerta de Red ---")
    payload = {
        "alert_id": "ZB-888",
        "server_id": "core-db-02",
        "data": "BGP Session Down: Neighbor Peer 10.0.0.1",
        "urgency_level": 5
    }
    response = requests.post(f"{BASE_URL}/webhook", json=payload)
    print(f"Estado: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    # Asegúrate de que el servidor FastAPI esté ejecutándose con:
    # uvicorn src.server:app --reload
    try:
        test_webhook_hardware()
        test_webhook_network()
    except requests.exceptions.ConnectionError:
        print("Error: No se ha podido conectar al servidor FastAPI. ¿Está en ejecución?")
