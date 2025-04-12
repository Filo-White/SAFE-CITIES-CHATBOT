import streamlit as st
import os
from chatbot import SafeCitiesChatbot
import yaml
import pandas as pd
import time
from datetime import datetime
import uuid

# Configurazione della pagina
st.set_page_config(
    page_title="Safe Cities Chatbot",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

def configure_api_keys():
    """Configura le chiavi API da variabili d'ambiente, file o input utente"""
    config = load_config()
    api_key = None
    
    # Prima controlla le variabili d'ambiente
    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    # Poi controlla il file di configurazione
    if not api_key and "api_keys" in config and config["api_keys"].get("openai"):
        api_key = config["api_keys"].get("openai")
    
    # Poi controlla se è presente un file di API keys
    api_key_file = config.get("api_keys", {}).get("api_key_file", "config/.api_keys")
    if not api_key and os.path.exists(api_key_file):
        try:
            with open(api_key_file, "r") as f:
                api_key = f.read().strip()
        except Exception as e:
            st.sidebar.warning(f"Error reading API key file: {e}")
    
    # Se ancora non abbiamo un API key, chiedila all'utente
    if not api_key:
        api_key = st.sidebar.text_input("OpenAI API Key", type="password", key="api_key_input")
        
        # Opzione per ricordare l'API key
        remember_key = config.get("api_keys", {}).get("remember_key", False)
        if api_key and st.sidebar.checkbox("Remember API key for future sessions", value=remember_key):
            try:
                # Crea la directory se non esiste
                os.makedirs(os.path.dirname(api_key_file), exist_ok=True)
                with open(api_key_file, "w") as f:
                    f.write(api_key)
                st.sidebar.success("API key saved for future sessions")
            except Exception as e:
                st.sidebar.error(f"Error saving API key: {e}")
    
    # Imposta l'API key nella variabile d'ambiente
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    return api_key is not None and api_key != ""

# Carica configurazione
@st.cache_resource
def load_config():
    """Carica il file di configurazione"""
    try:
        with open("config/config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.warning(f"Error loading configuration: {e}")
        # Configurazione di fallback
        return {
            "paths": {
                "sva_framework": "./docs/sva_framework",
                "gorizia_event": "./docs/gorizia_event",
                "simulation_templates": "./templates/simulations"
            },
            "models": {
                "chat_model": "gpt-4",
                "temperature": 0.7
            },
            "simulation": {
                "default_participants": 2000,
                "default_severity": 3
            }
        }

# Inizializza o carica il chatbot
@st.cache_resource
def initialize_chatbot(api_key=None):
    """Inizializza il chatbot (carica i documenti solo una volta)"""
    with st.spinner("Initializing chatbot... This may take a moment."):
        try:
            chatbot = SafeCitiesChatbot(api_key=api_key)
            # Imposta un flag per indicare che i documenti sono già stati caricati
            chatbot._documents_loaded = True
            return chatbot
        except Exception as e:
            st.error(f"Error initializing chatbot: {e}")
            return None

# Funzioni di utilità per l'interfaccia
def get_chat_mode_description(mode):
    """Ottiene la descrizione per una modalità di chat"""
    descriptions = {
        "auto": "Automatic mode - The system will determine the most appropriate type of response",
        "sva_framework": "SVA Framework Information - Responses based on official documentation",
        "event_planning": "Event Planning - Specific advice for organizing in Gorizia",
        "simulation": "Scenario Simulation - Generates a detailed simulation of adverse events"
    }
    return descriptions.get(mode, "")

def format_scenario_name(name):
    """Formatta il nome di uno scenario per la visualizzazione"""
    return name.replace("_", " ").title()

def generate_session_id():
    """Genera un ID univoco per la sessione"""
    return str(uuid.uuid4())

# Funzione per il reset della chat
def reset_chat():
    """Resetta la chat, mantenendo le impostazioni della sessione"""
    st.session_state.messages = []
    
    # Crea un nuovo ID sessione
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_session_id()
    
    # Aggiorna anche il chatbot
    if "chatbot" in st.session_state and st.session_state.chatbot:
        st.session_state.chatbot.reset_conversation()
    
    # Aggiungi nuovamente il messaggio di benvenuto
    welcome_message = {
        "role": "assistant",
        "content": """
        👋 Welcome to the Safe Cities Chatbot!
        
        I'm here to help you with:
        - Information on the SVA framework for safe cities
        - Event planning safety in Piazza Transalpina, Gorizia
        - Emergency scenario simulations
        
        How can I assist you today?
        """
    }
    st.session_state.messages.append(welcome_message)

# Funzione principale
def main():
    # Verifica l'API key
    api_key_configured = configure_api_keys()
    if not api_key_configured:
        st.warning("Please enter your OpenAI API key in the sidebar to continue.")
        return
    
    with st.sidebar:
        # Logo e titolo
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("assets/logo.png", width=80)  # Assicurati che il file esista nella cartella "assets"
        with col2:
            st.title("Safe-Cities Chatbot")
        
        st.markdown("---")
        
        st.subheader("Conversation Mode")
        
        # Selezione della modalità
        chat_mode = st.radio(
            "Select response mode:",
            options=["auto", "sva_framework", "event_planning", "simulation"],
            format_func=lambda x: x.replace("_", " ").title(),
            index=0
        )
        
        st.markdown(get_chat_mode_description(chat_mode))
        
        # Carica il chatbot
        chatbot = initialize_chatbot()
        
        # Nella sezione della sidebar di app.py dove si impostano i parametri di simulazione
# RIMUOVI questo blocco o sostituiscilo con il seguente:

        # Opzioni specifiche per la simulazione
        if chat_mode == "simulation":
            st.sidebar.subheader("Simulation Options")
            
            try:
                scenario_types = chatbot.get_available_scenarios()
                
                scenario_type = st.sidebar.selectbox(
                    "Scenario type:",
                    options=scenario_types,
                    format_func=format_scenario_name
                )
                
                severity = st.sidebar.slider(
                    "Event severity:",
                    min_value=1, max_value=5, value=3,
                    help="1 = Minor, 5 = Catastrophic"
                )
                
                # Nota: non chiediamo più il numero di partecipanti qui
                # Useremo invece quello impostato nell'event planning
                
                # Imposta i parametri di simulazione nel chatbot
                if chatbot:
                    # Crea un dizionario di parametri che NON include participants
                    chatbot.set_simulation_parameters({
                        "scenario_type": scenario_type,
                        "severity": severity
                    })
                    
                    # Mostra informazioni sui parametri ereditati
                    event_config = chatbot.config.get("event_planning", {})
                    if event_config:
                        st.sidebar.info(
                            f"The simulation will use these parameters from event planning:\n"
                            f"- Location: {event_config.get('location', 'Piazza Transalpina')}\n"
                            f"- Event type: {event_config.get('event_type', 'Public event')}\n"
                            f"- Attendance: {event_config.get('attendance', 2000)} people"
                        )
            except Exception as e:
                st.error(f"Error loading simulation options: {e}")

        # Opzioni specifiche per event planning
       # Opzioni specifiche per event planning
        if chat_mode == "event_planning":
            st.sidebar.subheader("Event Planning Options")
            
            location = st.sidebar.selectbox(
                "Select location:",
                options=["Any location", "Piazza Transalpina/Trg Evrope", "Custom location"],
                index=0
            )
            
            if location == "Custom location":
                custom_location = st.sidebar.text_input("Enter location name:")
                if custom_location:
                    location = custom_location
            
            event_type = st.sidebar.selectbox(
                "Type of event:",
                options=["Any event", "Concert", "Cultural event", "Festival", "Public gathering", "Sports event", "Other"],
                index=0
            )
            
            if event_type == "Other":
                custom_event = st.sidebar.text_input("Enter event type:")
                if custom_event:
                    event_type = custom_event
            
            attendance = st.sidebar.slider(
                "Estimated attendance:",
                min_value=100, max_value=10000, value=2000, step=100
            )
            
            # Aggiorna i parametri di event planning
            if chatbot:
                chatbot.set_event_planning_parameters({
                    "location": location,
                    "event_type": event_type,
                    "attendance": attendance
                })
        st.markdown("---")

        
        # Pulsante per salvare/caricare la conversazione
        if st.button("Save Conversation"):
            if "messages" in st.session_state and st.session_state.messages:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"conversation_{timestamp}.json"
                
                if chatbot:
                    chatbot.save_conversation(filename)
                    st.success(f"Conversation saved as {filename}")
        
        # Pulsante per il reset della chat
        if st.button("Reset Chat"):
            reset_chat()
            st.success("Chat reset successfully!")
        
        st.markdown("---")
        st.markdown("Developed with ❤️ for public safety")
    
    # Main area
    st.title("Safe Cities Assistant")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
        # Welcome message
        welcome_message = {
            "role": "assistant",
            "content": """
            👋 Welcome to the Safe Cities Chatbot!
            
            I'm here to help you with:
            - Information on the SVA framework for safe cities
            - Event planning safety in Piazza Transalpina, Gorizia
            - Emergency scenario simulations
            
            How can I assist you today?
            """
        }
        st.session_state.messages.append(welcome_message)
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_session_id()
    
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = chatbot
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # User input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get chatbot response
        if not st.session_state.chatbot:
            error_message = "Chatbot is not initialized. Please check the logs for errors."
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"):
                st.markdown(error_message)
        else:
            with st.spinner("Thinking..."):
                try:
                    # Process query
                    response = st.session_state.chatbot.process_query(prompt, mode=chat_mode)
                    
                    # Add response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    with st.chat_message("assistant"):
                        st.markdown(response)
                except Exception as e:
                    error_message = f"Error processing query: {str(e)}"
                    st.session_state.messages.append({"role": "assistant", "content": error_message})
                    with st.chat_message("assistant"):
                        st.markdown(error_message)
                    st.error(error_message)

if __name__ == "__main__":
    main()