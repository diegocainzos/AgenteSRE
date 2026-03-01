import unittest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.agent import create_graph_agent, ZabbixAlert

class TestAgentUnit(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Compila el agente una vez para todos los tests
        cls.agent = create_graph_agent().compile()

        # Carga los escenarios de prueba desde el archivo JSON
        with open("data/test_cases.json", "r") as f:
            cls.test_cases = json.load(f)

    async def test_alert_processing(self):
        """Itera a través de los casos de prueba verificando el comportamiento (Async)"""
        for case in self.test_cases:
            with self.subTest(case_name=case["name"]):
                print(f"\n[Test en ejecución]: {case['name']}")

                # Prepara el payload de entrada
                alert_payload = ZabbixAlert(**case["payload"])

                # Llama al agente de forma asíncrona
                result = await self.agent.ainvoke({"zabbix_alert": alert_payload})

                # Verifica la decisión del Router
                decision = result["router_decision"]
                self.assertEqual(
                    decision.category, 
                    case["expected_category"],
                    f"Esperaba la categoría {case['expected_category']}, pero obtuvo {decision.category}"
                )
                
                # Verifica la generación correcta del ticket
                ticket = result["easyvista_ticket"]
                self.assertIsNotNone(ticket.title)
                self.assertIsNotNone(ticket.details)
                
                # Busca las palabras clave de validación en la salida generada
                found_keywords = [
                    kw for kw in case["expected_keywords"] 
                    if kw.lower() in ticket.details.lower() or kw.lower() in ticket.summary.lower()
                ]
                
                print(f"   Categoría detectada: {decision.category} (OK)")
                print(f"   Palabras clave presentes: {found_keywords}")
                
                # Se espera que el ticket incluya al menos una palabra clave de la solución original
                self.assertTrue(
                    len(found_keywords) > 0, 
                    f"No se han encontrado las palabras clave esperadas {case['expected_keywords']} en los detalles del ticket."
                )

if __name__ == "__main__":
    unittest.main()
