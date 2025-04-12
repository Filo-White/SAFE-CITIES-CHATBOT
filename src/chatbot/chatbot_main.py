
import os
import yaml
from typing import Dict, List, Any, Optional, Tuple
import json

from .openai_client import OpenAIClient
from .document_store import DocumentStore, Document
from .memory import ConversationMemory
from .simulation import SimulationEngine

class SafeCitiesChatbot:
    """
    Classe principale del chatbot Safe Cities che integra tutti i componenti
    """
    
    def __init__(
        self,
        config_path: str = "config/config.yaml",
        prompts_path: str = "config/prompts.yaml",
        api_key: Optional[str] = None
    ):
        """
        Inizializza il chatbot Safe Cities
        
        Args:
            config_path: Percorso del file di configurazione
            prompts_path: Percorso del file dei prompt
            api_key: Chiave API OpenAI (opzionale, usa variabile d'ambiente se non specificata)
        """
        # Carica la configurazione
        self.config = self._load_yaml(config_path) or {}
        self.prompts = self._load_yaml(prompts_path) or {}
        
        # Inizializza il client OpenAI
        model_config = self.config.get("models", {})
        model_name = model_config.get("chat_model", "gpt-4")
        temperature = model_config.get("temperature", 0.7)
        
        self.openai_client = OpenAIClient(
            api_key=api_key,
            model=model_name,
            temperature=temperature
        )
        
        # Inizializza lo store dei documenti
        self.document_store = DocumentStore(self.openai_client.client)
        
        # Carica i documenti se specificati nella configurazione
        self._load_documents()
        
        # Inizializza il motore di simulazione
        templates_path = self.config.get("paths", {}).get("simulation_templates", "./templates/simulations")
        self.simulation_engine = SimulationEngine(self.openai_client, templates_path)
        
        # Inizializza la memoria della conversazione
        max_messages = self.config.get("memory", {}).get("max_messages", 50)
        self.memory = ConversationMemory(max_messages=max_messages)
        
        # Imposta il messaggio di sistema iniziale
        system_message = self.prompts.get("system_message", "")
        if system_message:
            self.memory.set_system_message(system_message)
    
    def _load_yaml(self, path: str) -> Dict:
        """Carica un file YAML"""
        if not os.path.exists(path):
            print(f"Il file {path} non esiste.")
            return {}
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Errore nel caricamento del file YAML {path}: {e}")
            return {}
    
    def _load_documents(self) -> None:
        """Carica i documenti specificati nella configurazione"""
        paths = self.config.get("paths", {})
        
        # Carica i documenti SVA
        sva_path = paths.get("sva_framework")
        if sva_path and os.path.exists(sva_path):
            print(f"Caricamento documenti SVA da {sva_path}...")
            self.document_store.load_documents_from_directory(sva_path, "sva_framework")
        
        # Carica i documenti sull'evento a Gorizia
        event_path = paths.get("gorizia_event")
        if event_path and os.path.exists(event_path):
            print(f"Caricamento documenti evento da {event_path}...")
            self.document_store.load_documents_from_directory(event_path, "gorizia_event")
        
        # Opzionalmente, carica embedding precompututati
        embeddings_path = paths.get("embeddings")
        if embeddings_path and os.path.exists(embeddings_path):
            print(f"Caricamento embeddings da {embeddings_path}...")
            self.document_store.load_from_file(embeddings_path)
        
    def set_event_planning_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Imposta i parametri per l'event planning
        
        Args:
            parameters: Dizionario di parametri (location, event_type, attendance, ecc.)
        """
        # Aggiorna la configurazione di event planning
        event_config = self.config.get("event_planning", {})
        event_config.update(parameters)
        self.config["event_planning"] = event_config    
    
    
    def process_query(self, query: str, mode: str = "auto") -> str:
        """
        Processa una query dell'utente
        
        Args:
            query: Testo della query dell'utente
            mode: Modalità di risposta ('auto', 'sva_framework', 'event_planning', 'simulation', 'conversational')
            
        Returns:
            Risposta del chatbot
        """
        print(f"Processing query in mode: {mode}")
        
        # Aggiungi il messaggio dell'utente alla memoria
        self.memory.add_message("user", query)
        
        # Determina automaticamente la modalità se richiesto
        if mode == "auto":
            mode = self._detect_query_mode(query)
            print(f"Auto-detected mode: {mode}")
        
        # Gestisci le domande specifiche sulle simulazioni disponibili
        if mode == "simulation" and any(
            phrase in query.lower() for phrase in [
                "what can i simulate", "what scenarios", "what simulations", 
                "what type of simulations", "what kind of scenarios"
            ]
        ):
            # Cambia a modalità conversazionale per domande informative
            mode = "conversational"
        
        # Processa la query in base alla modalità
        if mode == "simulation":
            # Verifica se la query è adatta alla simulazione
            if len(query.split()) < 4:  # Query troppo breve per essere una richiesta di simulazione completa
                # Passa alla modalità conversazionale per chiedere più dettagli
                mode = "conversational"
                print(f"Query too short for simulation, switching to conversational mode")
        
        # Gestisci in base alla modalità finale
        if mode == "simulation":
            response = self._handle_simulation_query(query)
        elif mode == "conversational":
            response = self._handle_conversational_query(query)
        else:
            response = self._handle_information_query(query, mode)
        
        # Aggiungi la risposta alla memoria
        self.memory.add_message("assistant", response)
    
        return response

    def _handle_conversational_query(self, query: str) -> str:
        """
        Gestisce una query conversazionale generale
        
        Args:
            query: Testo della query
            
        Returns:
            Risposta conversazionale
        """
        # Verifica se la query è relativa ai tipi di simulazione disponibili
        simulation_info_keywords = [
            "what can i simulate", "what scenarios", "what simulations", 
            "what type of simulations", "what kind of scenarios", "available simulations"
        ]
        
        if any(keyword in query.lower() for keyword in simulation_info_keywords):
            # Ottieni gli scenari effettivamente disponibili
            available_scenarios = self.simulation_engine.list_available_scenarios()
            
            # Formatta i nomi degli scenari per la visualizzazione
            formatted_scenarios = [s.replace("_", " ").title() for s in available_scenarios]
            
            # Crea una risposta personalizzata con gli scenari effettivamente disponibili
            custom_response = f"""
            I can simulate the following emergency scenarios for events:
            
            - {", ".join(formatted_scenarios)}
            
            To run a simulation, you can ask something like "Simulate a {available_scenarios[0]} scenario during a concert in Piazza Transalpina" or "What would happen if there was a {available_scenarios[1]} during an event with 3000 people?"
            
            You can specify parameters like the location, event type, number of attendees, and severity level.
            """
            
            return custom_response.strip()
        
        # Ottieni il prompt conversazionale
        conversational_prompt = self.prompts.get("conversational_prompt", "")
        
        if not conversational_prompt:
            # Usa un prompt di default per la modalità conversazionale
            conversational_prompt = """
            You are an assistant specialized in safe cities, security planning, and emergency management.
            You can help with:
            1. Providing information about the SVA (Structural Vulnerability Assessment) framework
            2. Offering advice on event planning and security in different locations, including Piazza Transalpina
            3. Generating simulations of various emergency scenarios
            
            Respond in a helpful and concise manner, directly addressing the user's question.
            Do not mention GO!2025 or GO!Gorizia unless specifically asked about it.
            
            User query: {query}
            """
        
        # Prepara il prompt completo
        full_prompt = conversational_prompt.format(query=query)
        
        # Ottieni la storia della conversazione
        conversation_history = self.memory.get_openai_messages()
        
        # Assicurati che il sistema sappia di cosa è capace il chatbot
        has_system_message = False
        for msg in conversation_history:
            if msg["role"] == "system":
                has_system_message = True
                break
        
        if not has_system_message:
            # Aggiungi un messaggio di sistema se non c'è
            system_message = {
                "role": "system", 
                "content": self.prompts.get("system_message", "You are an assistant for safe cities and emergency planning.")
            }
            conversation_history.insert(0, system_message)
        
        # Non sostituire l'ultima query dell'utente, lasciala naturale
        # Invece, aggiungi un nuovo messaggio utente con il prompt completo
        conversation_history.append({"role": "user", "content": full_prompt})
        
        # Tronca la conversazione se necessario
        truncated_messages = self.openai_client.truncate_messages_to_fit_context(
            conversation_history, 
            max_tokens=4000
        )
        
        # Genera la risposta
        response = self.openai_client.generate_response(truncated_messages, temperature=0.7)
        
        # Verifica che la risposta non contenga riferimenti a GO!Gorizia se non richiesto
        if "GO!2025" not in query and "GO! 2025" not in query and "gogorizia" not in query.lower() and ("GO!2025" in response or "GO! 2025" in response):
            # Aggiungi una nota per rimuovere i riferimenti non richiesti
            clarification = "Your response contains references to GO!2025 or GO!Gorizia, which wasn't mentioned in my query. Please provide a general response without mentioning GO!2025."
            
            # Genera una risposta corretta
            corrected_messages = [
                {"role": "system", "content": "You are an assistant for safe cities and emergency planning. Do not mention GO!2025 or GO!Gorizia unless specifically asked about it."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": response},
                {"role": "user", "content": clarification}
            ]
            
            response = self.openai_client.generate_response(corrected_messages)
        
        return response
    
    def _detect_query_mode(self, query: str) -> str:
        """
        Determina automaticamente la modalità più appropriata per una query
        
        Args:
            query: Testo della query
            
        Returns:
            Modalità rilevata ('sva_framework', 'event_planning', 'simulation', 'conversational')
        """
        query_lower = query.lower()
        
        # Rilevamento più preciso per le richieste di simulazione
        simulation_phrases = [
            "simulate a", "simulate an", "create a simulation", "run a simulation",
            "simulate what happens", "create a scenario"
        ]
        
        # Rilevamento per le richieste di informazioni su simulazioni
        simulation_info_phrases = [
            "what can i simulate", "what scenarios", "what simulations", 
            "what type of simulations", "what kind of scenarios"
        ]
        
        # Parole chiave per la simulazione in contesto specifico
        simulation_context_keywords = [
            "emergency", "attack", "disaster", "incident", "security event"
        ]
        
        # Parole chiave precise per l'event planning (richiede contesto più specifico)
        event_planning_phrases = [
            "organize an event", "plan an event", "event security", "event safety",
            "organize a concert", "plan a festival", "event planning", "security measures for event"
        ]
        
        # Parole chiave specifiche per Piazza Transalpina
        transalpina_keywords = [
            "piazza transalpina", "transalpina square", "gorizia", "nova gorica", "cross-border"
        ]
        
        # Parole chiave per il framework SVA
        sva_keywords = [
            "sva framework", "structural vulnerability", "vulnerability assessment",
            "security assessment", "sva methodology", "threat assessment"
        ]
        
        # Verifica domande informative sulle simulazioni
        if any(phrase in query_lower for phrase in simulation_info_phrases):
            return "conversational"
        
        # Verifica richieste esplicite di simulazione
        if any(phrase in query_lower for phrase in simulation_phrases):
            return "simulation"
        
        # Verifica esplicita per event planning
        is_event_planning = any(phrase in query_lower for phrase in event_planning_phrases)
        is_transalpina = any(keyword in query_lower for keyword in transalpina_keywords)
        
        # Se parla di event planning E di Transalpina, usa la modalità event_planning
        if is_event_planning and is_transalpina:
            return "event_planning"
        
        # Se parla solo di event planning generico, usa anche event_planning ma senza assumere Transalpina
        if is_event_planning:
            return "event_planning"
        
        # Se menziona specificamente Transalpina ma non event planning, potrebbe essere una domanda sulla location
        if is_transalpina:
            return "event_planning"  # Usa event_planning ma il prompt gestirà il contesto
        
        # Verifica parole chiave SVA specifiche
        if any(keyword in query_lower for keyword in sva_keywords):
            return "sva_framework"
        
        # Verifica se ci sono parole chiave di simulazione in contesto appropriato
        if any(keyword in query_lower for keyword in simulation_context_keywords):
            if "what happens" in query_lower or "what would happen" in query_lower:
                return "simulation"
        
        # Per query più generiche, usa la modalità conversazionale
        return "conversational"
        
    def _handle_information_query(self, query: str, mode: str) -> str:
        """
        Gestisce una query informativa sul framework SVA o sull'event planning,
        con migliore utilizzo dei parametri specificati
        
        Args:
            query: Testo della query
            mode: Modalità specifica ('sva_framework' o 'event_planning')
            
        Returns:
            Risposta informativa
        """
        # Ottieni il prompt appropriato per la modalità
        prompt_key = f"{mode}_prompt"
        prompt_template = self.prompts.get(prompt_key, "")
        
        # Usa un prompt di default se non è disponibile uno specifico
        if not prompt_template:
            if mode == "sva_framework":
                prompt_template = """
                You are an expert in the SVA (Structural Vulnerability Assessment) framework for safe cities.
                Provide accurate, detailed information based on the context provided.
                
                User query: {query}
                
                Relevant context:
                {context}
                
                Respond in a clear, structured manner. If some information is not available in the context, 
                mention this explicitly.
                """
            elif mode == "event_planning":
                prompt_template = """
                You are a security consultant specialized in organizing events using the SVA framework principles.
                Provide practical advice and specific security measures for events.
                
                User query: {query}
                
                Relevant context:
                {context}
                
                Parameters:
                {parameters}
                
                Your response should be practical, actionable, and focused on security planning.
                Specifically incorporate the provided parameters in your response.
                
                DO NOT mention GO!2025 or GO!Gorizia unless specifically asked about it in the query.
                """
        
        # Recupera il contesto rilevante dai documenti
        search_query = query
        
        # Ottieni i parametri event planning
        parameters_str = ""
        
        # Se siamo in modalità event planning, migliora la query di ricerca con i parametri
        if mode == "event_planning":
            event_config = self.config.get("event_planning", {})
            location = event_config.get("location", "")
            event_type = event_config.get("event_type", "")
            attendance = event_config.get("attendance", 0)
            
            # Crea una stringa di parametri da inserire nel prompt
            parameters_str = "Location: "
            if location and location != "Any location":
                parameters_str += f"{location}\n"
                # Aggiungi alla query di ricerca
                search_query += f" {location}"
            else:
                parameters_str += "Not specified\n"
            
            parameters_str += "Event type: "
            if event_type and event_type != "Any event":
                parameters_str += f"{event_type}\n"
                # Aggiungi alla query di ricerca
                search_query += f" {event_type}"
            else:
                parameters_str += "Not specified\n"
            
            parameters_str += "Estimated attendance: "
            if attendance > 0:
                parameters_str += f"{attendance} people\n"
                # Aggiungi alla query di ricerca
                search_query += f" {attendance} attendees"
            else:
                parameters_str += "Not specified\n"
        
        # Verifica se GO!Gorizia è specificamente menzionato
        use_gogorizia = "GO!2025" in query or "GO! 2025" in query or "gogorizia" in query.lower()
        
        # Ottieni il contesto dai documenti
        if use_gogorizia:
            context = self.document_store.get_context_for_query(search_query + " GO!2025")
        else:
            context = self.document_store.get_context_for_query(search_query)
        
        # Se siamo in modalità event planning, aggiungi informazioni sulla location
        if mode == "event_planning":
            event_config = self.config.get("event_planning", {})
            location = event_config.get("location", "")
            
            # Se Piazza Transalpina è selezionata, aggiungi informazioni specifiche
            if location == "Piazza Transalpina/Trg Evrope" or "transalpina" in location.lower():
                transalpina_info = self.document_store.search("piazza transalpina layout safety", top_k=2)
                if transalpina_info:
                    transalpina_context = "\n\n".join([doc.text for doc in transalpina_info])
                    context = f"{context}\n\nSpecific information about Piazza Transalpina:\n{transalpina_context}"
                else:
                    # Aggiungi informazioni di base se non ci sono documenti specifici
                    context += """
                    
                    Specific information about Piazza Transalpina:
                    Piazza Transalpina/Trg Evrope is a square located at the border between Italy (Gorizia) and Slovenia (Nova Gorica). 
                    It has a symbolic importance as it represents European unity. The square has an irregular shape of approximately 5000 square meters,
                    with three main access points. It can accommodate up to 5000 people and is bordered by buildings on two sides.
                    Any event here requires coordination between Italian and Slovenian authorities for security, emergency response, and logistics.
                    """
        
        # Se non c'è contesto, usa una risposta basata sulla conoscenza generale
        if not context:
            if mode == "sva_framework":
                context = "No specific information available in the documents. Providing general knowledge about the SVA framework."
            elif mode == "event_planning":
                context = "No specific information available in the documents. Providing general advice for event security planning."
            else:
                context = "No specific information available in the documents. Providing general knowledge response."
        
        # Aggiungi istruzioni per evitare riferimenti a GO!Gorizia se non richiesto
        if mode == "event_planning" and not use_gogorizia:
            context += "\n\nIMPORTANT: Do not mention GO!2025 or GO!Gorizia in your response unless specifically asked about it."
        
        # Prepara il prompt completo
        if mode == "event_planning":
            full_prompt = prompt_template.format(query=query, context=context, parameters=parameters_str)
        else:
            full_prompt = prompt_template.format(query=query, context=context)
        
        # Prepara i messaggi per OpenAI
        conversation_history = self.memory.get_openai_messages()
        
        # Assicurati che il prompt sia inserito nell'ultimo messaggio utente
        for i in range(len(conversation_history) - 1, -1, -1):
            if conversation_history[i]["role"] == "user":
                conversation_history[i]["content"] = full_prompt
                break
        
        # Tronca la conversazione se necessario
        truncated_messages = self.openai_client.truncate_messages_to_fit_context(
            conversation_history, 
            max_tokens=4000
        )
        
        # Genera la risposta
        response = self.openai_client.generate_response(truncated_messages)
        
        # Verifica che la risposta non contenga riferimenti a GO!Gorizia se non richiesto
        if mode == "event_planning" and not use_gogorizia and ("GO!2025" in response or "GO! 2025" in response):
            # Aggiungi una nota per rimuovere i riferimenti non richiesti
            conversation_history.append({"role": "assistant", "content": response})
            conversation_history.append({
                "role": "user", 
                "content": "Your response contains references to GO!2025 or GO!Gorizia, which wasn't mentioned in my query. Please revise your response to provide general event planning advice without mentioning GO!2025 specifically."
            })
            
            # Genera una risposta corretta
            response = self.openai_client.generate_response(conversation_history[-2:])
        
        return response
    
    def _handle_simulation_query(self, query: str) -> str:
        """
        Gestisce una query di simulazione incorporando meglio i parametri specificati
        
        Args:
            query: Testo della query
            
        Returns:
            Simulazione generata
        """
        # Ottieni i parametri di simulazione configurati
        simulation_config = self.config.get("simulation", {})
        scenario_type = simulation_config.get("scenario_type", None)
        participants = simulation_config.get("participants", 2000)
        severity = simulation_config.get("severity", 3)
        
        # Se GO!Gorizia è specificamente menzionato, usa quel contesto
        use_gogorizia = "GO!2025" in query or "GO! 2025" in query or "gogorizia" in query.lower()
        
        # Recupera informazioni di contesto sull'evento
        event_context = ""
        
        # Se GO!Gorizia è menzionato, cerca specificamente quel contesto
        if use_gogorizia:
            event_docs = self.document_store.search("GO!2025 event gorizia", top_k=2)
            if event_docs:
                event_context = "\n\n".join([doc.text for doc in event_docs])
            else:
                event_context = (
                    "The GO!2025 event is a major cultural event taking place in Gorizia and Nova Gorica, "
                    "with Piazza Transalpina/Trg Evrope serving as a focal point for cross-border activities. "
                    f"The event attracts approximately {participants} attendees to the square."
                )
        else:
            # Altrimenti, usa un contesto più generico basato sui parametri specificati
            # Ottieni eventuali parametri di event planning
            event_config = self.config.get("event_planning", {})
            location = event_config.get("location", "Piazza Transalpina/Trg Evrope")
            event_type = event_config.get("event_type", "public event")
            attendance = event_config.get("attendance", participants)
            
            if location == "Any location":
                location = "Piazza Transalpina/Trg Evrope"
            
            if event_type == "Any event":
                event_type = "public event"
            
            # Costruisci un contesto basato sui parametri
            event_context = (
                f"A {event_type} is taking place in {location} with approximately {attendance} attendees. "
                f"The event has been planned with a security level appropriate for a severity level {severity}/5."
            )
            
            # Aggiungi solo dettagli sulla location se è Piazza Transalpina
            if "transalpina" in location.lower():
                location_docs = self.document_store.search("piazza transalpina layout", top_k=1)
                if location_docs:
                    event_context += "\n\n" + location_docs[0].text
        
        # Recupera informazioni sulla location
        location_context = ""
        
        # Usa l'event_config per determinare la location
        event_config = self.config.get("event_planning", {})
        location = event_config.get("location", "Piazza Transalpina/Trg Evrope")
        
        if location == "Any location":
            location = "Piazza Transalpina/Trg Evrope"
        
        # Cerca informazioni specifiche sulla location specificata
        location_docs = self.document_store.search(f"{location} layout security", top_k=2)
        if location_docs:
            location_context = "\n\n".join([doc.text for doc in location_docs])
        elif "transalpina" in location.lower():
            # Informazioni di default su Piazza Transalpina
            location_context = (
                "Piazza Transalpina/Trg Evrope is located at the border between Italy (Gorizia) and Slovenia (Nova Gorica). "
                "It has an irregular shape of approximately 5000 square meters. "
                "It has three main access routes and can accommodate up to 5000 people. "
                "The square is bordered by buildings on two sides and open on the other two."
            )
        else:
            # Informazioni generiche per altre location
            location_context = (
                f"{location} is the venue for this event. "
                f"Standard security protocols for a public space of this nature apply."
            )
        
        # Prepara il contesto aggiuntivo basato sui parametri specificati
        additional_context = {
            "participants": participants,
            "severity": severity,
            "scenario_type": scenario_type,
            "location": location,
            "event_type": event_config.get("event_type", "public event"),
            "is_gogorizia": use_gogorizia
        }
        
        # Rileva automaticamente il tipo di scenario se non specificato
        if not scenario_type:
            scenario_type = self.simulation_engine.detect_scenario_type(query)
        
        # Fornisci istruzioni aggiuntive al motore di simulazione
        instructions = ""
        if not use_gogorizia:
            instructions = (
                "Do not mention GO!2025 or GO!Gorizia unless specifically asked about it. "
                "Focus on the generic event described with the parameters provided."
            )
        
        # Genera la simulazione
        simulation = self.simulation_engine.generate_simulation(
            query=query,
            event_context=event_context,
            location_context=location_context,
            additional_context=additional_context,
            scenario_type=scenario_type,
            additional_instructions=instructions
        )
        
        return simulation
        
    def set_simulation_parameters(self, parameters: Dict[str, Any]) -> None:
        """
        Imposta i parametri per la simulazione
        
        Args:
            parameters: Dizionario di parametri (scenario_type, participants, severity, ecc.)
        """
        # Aggiorna la configurazione di simulazione
        simulation_config = self.config.get("simulation", {})
        simulation_config.update(parameters)
        self.config["simulation"] = simulation_config
    
    def reset_conversation(self, keep_system: bool = True) -> None:
        """
        Resetta la conversazione
        
        Args:
            keep_system: Se True, mantiene il messaggio di sistema
        """
        self.memory.clear(keep_system=keep_system)
    
    def save_conversation(self, file_path: str) -> None:
        """
        Salva la conversazione corrente su file
        
        Args:
            file_path: Percorso del file di output
        """
        self.memory.save_to_file(file_path)
    
    def load_conversation(self, file_path: str) -> bool:
        """
        Carica una conversazione da file
        
        Args:
            file_path: Percorso del file di input
            
        Returns:
            True se il caricamento è riuscito, False altrimenti
        """
        return self.memory.load_from_file(file_path)
    
    def get_available_scenarios(self) -> List[str]:
        """
        Ottiene l'elenco dei tipi di scenari disponibili
        
        Returns:
            Lista dei tipi di scenari
        """
        return self.simulation_engine.list_available_scenarios()


if __name__ == "__main__":
    # Esempio di utilizzo
    from dotenv import load_dotenv
    load_dotenv()
    
    chatbot = SafeCitiesChatbot()
    
    # Test di una query sul framework SVA
    query = "What are the key principles of the SVA framework?"
    print(f"Query: {query}")
    response = chatbot.process_query(query, mode="sva_framework")
    print(f"Response: {response}\n")
    
    # Test di una query sulla pianificazione di eventi
    query = "What security measures should be implemented for a concert in Piazza Transalpina?"
    print(f"Query: {query}")
    response = chatbot.process_query(query, mode="event_planning")
    print(f"Response: {response}\n")
    
    # Test di una simulazione
    query = "Simulate a weather emergency during the event in the square"
    print(f"Query: {query}")
    response = chatbot.process_query(query, mode="simulation")
    print(f"Response: {response}")