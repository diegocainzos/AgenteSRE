import streamlit as st
import json
import asyncio
from src.agent import create_graph_agent, ZabbixAlert

# Configuramos la página de Streamlit
st.set_page_config(
    page_title="Agente SRE",
    page_icon="🚀",
    layout="wide"
)

# Estilos CSS personalizados para mejorar la interfaz
st.markdown("""
    <style>
    .stExpander { border: 1px solid #4B4B4B; border-radius: 5px; }
    .ticket-box { background-color: #1E1E1E; padding: 20px; border-radius: 10px; border-left: 5px solid #00FFAA; }
    .intro-box { background-color: #262730; padding: 20px; border-radius: 8px; border-left: 5px solid #FF4B4B; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# Almacenamos en caché la compilación del agente para no recompilar al recargar
@st.cache_resource
def get_agent():
    return create_graph_agent().compile()

agent = get_agent()

# Cargamos la batería de pruebas
@st.cache_data
def load_test_cases():
    with open("data/test_cases.json", "r") as f:
        return json.load(f)

test_cases = load_test_cases()

# --- PANEL LATERAL: Entrada de datos ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1869px-Python-logo-notext.svg.png", width=50)
st.sidebar.title("Simulador de Zabbix")
st.sidebar.markdown("Simula la entrada de alertas de infraestructura.")

case_names = [c["name"] for c in test_cases] + ["Alerta Personalizada"]
selected_case = st.sidebar.selectbox("Selecciona un Escenario", case_names)

if selected_case != "Alerta Personalizada":
    case_data = next(c["payload"] for c in test_cases if c["name"] == selected_case)
    alert_id = st.sidebar.text_input("ID de Alerta", case_data["alert_id"])
    server_id = st.sidebar.text_input("ID del Servidor", case_data["server_id"])
    data = st.sidebar.text_area("Descripción de la Alerta", case_data["data"])
    urgency = st.sidebar.slider("Nivel de Urgencia", 1, 5, case_data["urgency_level"])
else:
    alert_id = st.sidebar.text_input("ID de Alerta", "ZB-NUEVO")
    server_id = st.sidebar.text_input("ID del Servidor", "db-cluster-01")
    data = st.sidebar.text_area("Descripción de la Alerta", "Escribe tu error personalizado aquí...")
    urgency = st.sidebar.slider("Nivel de Urgencia", 1, 5, 3)

# --- PANEL PRINCIPAL ---
st.title("🚀 We Hunt: Agente de Auto-Remediación SRE")

# Introducción para el reclutador
st.markdown("""
<div class="intro-box">
    <h4>👋 ¡Hola, equipo de We Hunt!</h4>
    <p>Este dashboard demuestra una solución completa de <b>AI Engineering</b> diseñada para la automatización de operaciones (SRE).</p>
    <ul>
        <li><b>Orquestación:</b> Utiliza <code>LangGraph</code> (asíncrono) para gestionar el ciclo de vida del incidente de forma determinista.</li>
        <li><b>RAG Avanzado:</b> Emplea <code>Multi-Query Retrieval</code> y <code>ChromaDB</code> para consultar los manuales de infraestructura y superar las limitaciones de la búsqueda semántica estándar.</li>
        <li><b>Integraciones:</b> Simula la conexión con herramientas corporativas clave (<i>Zabbix</i> para alertas, <i>PhpIPAM</i> para inventario, y <i>EasyVista</i> para creación de tickets).</li>
    </ul>
    <p><i>Selecciona un escenario en el menú lateral y haz clic en "Disparar Webhook" para ver la ejecución del agente en tiempo real.</i></p>
</div>
""", unsafe_allow_html=True)

if st.sidebar.button("Disparar Webhook 🚨", type="primary"):
    
    # Preparamos el payload de la alerta
    alert_payload = ZabbixAlert(
        alert_id=alert_id, 
        server_id=server_id, 
        data=data, 
        urgency_level=urgency
    )
    
    st.markdown("### 🧠 Traza de Ejecución del Agente")
    
    # Contenedores estáticos para evitar errores de renderizado en React/Streamlit
    progress_bar = st.progress(0)
    status_text = st.empty()
    trace_container = st.container()
    
    # Usamos una función asíncrona para iterar el flujo de LangGraph
    async def run_agent_stream():
        step_count = 0
        total_expected_steps = 4 # phpipam -> router -> db/rag -> ticket
        
        async for event in agent.astream({"zabbix_alert": alert_payload}):
            for node_name, node_state in event.items():
                step_count += 1
                progress_bar.progress(int((step_count / total_expected_steps) * 100))
                status_text.markdown(f"**Estado Actual:** Ejecutando nodo `{node_name}`...")
                
                # Añadimos la respuesta al contenedor estático
                with trace_container.expander(f"✅ Nodo Completado: {node_name.upper()}", expanded=True):
                    
                    if node_name == "call_phpipam":
                        st.write("🌍 **Mock de PhpIPAM:** Alerta enriquecida con el contexto del servidor.")
                        st.json(node_state["server_info"].model_dump())
                        
                    elif node_name == "router_retriever":
                        decision = node_state["router_decision"]
                        st.write("🚦 **Router LLM:** Analizó la alerta y tomó una decisión de enrutamiento.")
                        col1, col2 = st.columns(2)
                        col1.metric("Ruta Seleccionada", decision.next_action)
                        col2.metric("Categoría Detectada", decision.category.upper())
                        st.info(f"**Razonamiento:** {decision.reasoning}")
                        
                    elif node_name in ["rag_bookstack", "logs_db"]:
                        st.write("📚 **Recuperación de Conocimiento:** Extrayendo pasos de resolución.")
                        st.success("Contexto recuperado con éxito usando Multi-Query Retrieval (RAG)." if node_name == "rag_bookstack" else "Búsqueda en base de datos de logs históricos simulada con éxito.")
                        with st.container(height=150):
                            st.markdown(node_state["retrieved_knowledge"])
                            
                    elif node_name == "create_easyvista_ticket":
                        st.write("🎫 **Generación de Ticket EasyVista:** Payload final sintetizado por el LLM.")
                        ticket = node_state["easyvista_ticket"]
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="ticket-box">
                            <h3 style='margin-top:0;'>{ticket.title}</h3>
                            <p><strong>Prioridad:</strong> P{ticket.priority}</p>
                            <p><strong>Resumen:</strong> {ticket.summary}</p>
                            <p><strong>Pasos de Resolución:</strong><br>{ticket.details}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
        status_text.markdown("**Estado Actual:** ¡Flujo Completado! 🎉")

    # Ejecutar la corrutina de Streamlit dentro de su propio bucle de eventos
    try:
        asyncio.run(run_agent_stream())
    except Exception as e:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_agent_stream())
