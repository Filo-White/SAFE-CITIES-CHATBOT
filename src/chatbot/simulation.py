import os
from typing import Dict, List, Any, Optional
import glob
import json
from .openai_client import OpenAIClient

class SimulationEngine:
    """Engine per la generazione di simulazioni di scenari di emergenza"""
    
    def __init__(
        self, 
        openai_client: OpenAIClient,
        templates_dir: str
    ):
        """
        Inizializza il motore di simulazione
        
        Args:
            openai_client: Istanza del client OpenAI
            templates_dir: Directory contenente i template di simulazione
        """
        self.client = openai_client
        self.templates_dir = templates_dir
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """Carica tutti i template dalla directory specificata"""
        templates = {}
        
        # Verifica che la directory esista
        if not os.path.exists(self.templates_dir):
            print(f"Attenzione: La directory {self.templates_dir} non esiste.")
            # Crea un template generico di fallback
            templates["generic"] = """
            # Generic Template for Emergency Simulation

            Create a detailed simulation of a generic emergency during a public event.
            
            ## Structure of the simulation:
            1. Describe the initial scenario of the event
            2. Describe the incident or emergency that occurs
            3. List the immediate actions to be taken
            4. Describe the evacuation plan
            5. Provide recommendations to improve security
            """
            return templates
        
        # Carica tutti i file .txt o .md come template
        for file_path in glob.glob(os.path.join(self.templates_dir, "*.md")) + \
                         glob.glob(os.path.join(self.templates_dir, "*.txt")):
            try:
                scenario_type = os.path.splitext(os.path.basename(file_path))[0]
                with open(file_path, "r", encoding="utf-8") as f:
                    templates[scenario_type] = f.read()
                print(f"Template caricato: {scenario_type}")
            except Exception as e:
                print(f"Errore nel caricamento del template {file_path}: {e}")
        
        # Verifica che ci sia almeno un template generico
        if not templates or "generic" not in templates:
            # Se non c'è un template generico, crea uno di base
            templates["generic"] = """
            # Generic Template for Emergency Simulation

            Create a detailed simulation of a generic emergency during a public event.
            
            ## Structure of the simulation:
            1. Describe the initial scenario of the event
            2. Describe the incident or emergency that occurs
            3. List the immediate actions to be taken
            4. Describe the evacuation plan
            5. Provide recommendations to improve security
            """
            
        return templates
    
    def detect_scenario_type(self, query: str) -> str:
        """
        Determina automaticamente il tipo di scenario dalla query dell'utente
        
        Args:
            query: Query dell'utente
        
        Returns:
            Tipo di scenario identificato
        """
        # Mappa di parole chiave per ogni tipo di scenario
        scenario_keywords = {
            "terrorism": ["terrorism", "attack", "bomb", "explosive", "terrorist", "terror"],
            "weather": ["weather", "storm", "rain", "tempest", "flood", "flooding", "meteorological"],
            "fire": ["fire", "flames", "blaze", "combustion", "burning"],
            "medical_emergency": ["medical", "health", "injury", "illness", "epidemic", "outbreak"],
            "violence": ["knife", "weapon", "violence", "aggression", "stab", "armed"],
            "public_disorder": ["disorder", "riot", "clash", "panic", "crowd", "stampede", "protest"]
        }
        
        # Check for keywords
        query_lower = query.lower()
        for scenario, keywords in scenario_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                # Verify we have a template for this scenario
                if scenario in self.templates:
                    return scenario
                else:
                    print(f"Scenario {scenario} identified but template not available")
        
        # If no specific scenario is identified, use generic
        return "generic"
    
    def generate_simulation(
        self, 
        query: str, 
        event_context: str,
        location_context: str,
        additional_context: Dict[str, Any] = None,
        scenario_type: Optional[str] = None,
        additional_instructions: str = ""
    ) -> str:
        """
        Genera una simulazione di scenario
        
        Args:
            query: Query dell'utente
            event_context: Informazioni sul contesto dell'evento
            location_context: Informazioni sulla location
            additional_context: Contesto aggiuntivo (partecipanti, gravità, ecc.)
            scenario_type: Tipo specifico di scenario (se None, viene rilevato automaticamente)
            additional_instructions: Istruzioni aggiuntive per il modello
            
        Returns:
            Testo della simulazione generata
        """
        # Determina il tipo di scenario se non specificato
        if scenario_type is None:
            scenario_type = self.detect_scenario_type(query)
        
        # Seleziona il template appropriato
        template = self.templates.get(scenario_type, self.templates.get("generic", "Create a detailed emergency simulation."))
        
        # Processa il contesto aggiuntivo
        context_str = ""
        is_gogorizia = False
        
        if additional_context:
            for key, value in additional_context.items():
                if key == "participants":
                    context_str += f"Number of participants: {value}\n"
                elif key == "severity":
                    context_str += f"Severity level (1-5): {value}\n"
                elif key == "location":
                    context_str += f"Location: {value}\n"
                elif key == "event_type":
                    context_str += f"Event type: {value}\n"
                elif key == "is_gogorizia":
                    is_gogorizia = value
                else:
                    context_str += f"{key}: {value}\n"
        
        # Aggiungi istruzioni sul GO!Gorizia
        if not is_gogorizia and not "GO!2025" in query and not "gogorizia" in query.lower():
            if not additional_instructions:
                additional_instructions = ""
            additional_instructions += "\nDo not refer to GO!2025 or GO!Gorizia unless specifically mentioned in the query."
        
        # Prepara il prompt per la generazione
        prompt = f"""
        # Simulation Request
        
        ## Query details
        {query}
        
        ## Event information
        {event_context}
        
        ## Location information
        {location_context}
        
        ## Additional context
        {context_str}
        
        ## Simulation template instructions
        {template}
        
        ## Additional guidance
        {additional_instructions}
        
        Use the exact parameters provided (number of participants, severity level, location, etc.) in your simulation.
        Make the simulation realistic and detailed, incorporating the specific context provided.
        """
        
        # Genera la simulazione usando OpenAI
        messages = [
            {"role": "system", "content": "You are an expert in emergency management and security planning for public events. Your task is to create detailed and realistic simulations of emergency scenarios based on specific templates and the exact parameters provided."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.generate_response(messages, temperature=0.7)
            
            # Format the response with a title
            scenario_names = {
                "terrorism": "Terrorist Attack",
                "weather": "Extreme Weather Event",
                "fire": "Fire Emergency",
                "medical_emergency": "Medical Emergency",
                "violence": "Armed Attack",
                "public_disorder": "Public Disorder",
                "generic": "Generic Emergency Scenario"
            }
            
            scenario_title = scenario_names.get(scenario_type, f"Scenario: {scenario_type}")
            
            formatted_response = f"""
            # Simulation: {scenario_title}
            
            {response}
            
            ---
            *Note: This is an artificially generated simulation for planning purposes.
            The information is based on the SVA framework principles for security planning.*
            """
            
            return formatted_response.strip()
            
        except Exception as e:
            print(f"Error during simulation generation: {e}")
            return f"Sorry, there was an error generating the simulation: {str(e)}"
    
    def list_available_scenarios(self) -> List[str]:
        """Returns the list of available scenario types"""
        return list(self.templates.keys())


if __name__ == "__main__":
    # Example usage
    from dotenv import load_dotenv
    load_dotenv()
    
    client = OpenAIClient()
    engine = SimulationEngine(client, "./templates/simulations")
    
    # Test the scenario detection
    query = "Simulate a terrorist attack during the concert in Piazza Transalpina"
    scenario_type = engine.detect_scenario_type(query)
    print(f"Detected scenario type: {scenario_type}")
    
    # Test simulation generation
    event_context = "Rock concert with approximately 3000 attendees expected. Main stage on the east side of the square."
    location_context = "Piazza Transalpina is located at the border between Italy and Slovenia. It has three main access routes."
    additional_context = {
        "participants": 3000,
        "severity": 4
    }
    
    # Generate simulation
    simulation = engine.generate_simulation(
        query=query,
        event_context=event_context,
        location_context=location_context,
        additional_context=additional_context
    )
    
    print("\nGenerated Simulation:")
    print(simulation)