import os
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
import tiktoken
import json
import time

class OpenAIClient:
    """Client per le interazioni con l'API OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4", temperature: float = 0.7):
        """
        Inizializza il client OpenAI
        
        Args:
            api_key: Chiave API OpenAI (opzionale, usa variabile d'ambiente se non specificata)
            model: Modello da utilizzare per la generazione di testo
            temperature: Temperatura per il controllo della creatività (0.0-1.0)
        """
        # Se api_key è fornito, usalo, altrimenti usa la variabile d'ambiente
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        
        # Inizializza il tokenizer
        self.tokenizer = tiktoken.encoding_for_model(model)
    
    def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Genera una risposta dal modello
        
        Args:
            messages: Lista di messaggi nel formato OpenAI (role, content)
            temperature: Temperatura per la generazione (usa il valore di default se None)
            max_tokens: Numero massimo di token nella risposta
        
        Returns:
            Testo della risposta generata
        """
        try:
            # Usa il valore di default se temperature non è specificato
            temp = temperature if temperature is not None else self.temperature
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens
            )
            
            # Estrai il testo della risposta
            return response.choices[0].message.content
        except Exception as e:
            print(f"Errore nella generazione della risposta: {e}")
            return f"Errore nella generazione della risposta: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """
        Conta il numero di token in un testo
        
        Args:
            text: Testo da tokenizzare
        
        Returns:
            Numero di token
        """
        return len(self.tokenizer.encode(text))
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Conta il numero di token in una lista di messaggi
        
        Args:
            messages: Lista di messaggi nel formato OpenAI (role, content)
        
        Returns:
            Numero totale di token
        """
        total_tokens = 0
        
        for message in messages:
            # Conta i token nel testo del messaggio
            total_tokens += self.count_tokens(message["content"])
            
            # Aggiungi token per i metadati del messaggio (approssimazione)
            total_tokens += 4  # ~4 token per role e formatting
        
        # Aggiungi token per il formato della richiesta
        total_tokens += 2  # ~2 token per il formato complessivo
        
        return total_tokens
    
    def truncate_messages_to_fit_context(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int = 4000,
        preserve_system: bool = True
    ) -> List[Dict[str, str]]:
        """
        Tronca i messaggi per adattarli al limite di token del contesto
        
        Args:
            messages: Lista di messaggi nel formato OpenAI
            max_tokens: Massimo numero di token consentito
            preserve_system: Se True, preserva sempre i messaggi di sistema
        
        Returns:
            Lista di messaggi troncata
        """
        if not messages:
            return []
        
        # Separa i messaggi di sistema dagli altri
        system_messages = [m for m in messages if m["role"] == "system"]
        other_messages = [m for m in messages if m["role"] != "system"]
        
        # Calcola i token utilizzati dai messaggi di sistema
        system_tokens = sum(self.count_tokens(m["content"]) + 4 for m in system_messages)
        
        # Spazio rimanente per gli altri messaggi
        remaining_tokens = max_tokens - system_tokens - 2  # 2 token per il formato
        
        # Se non c'è spazio sufficiente, riduci il contenuto dei messaggi di sistema
        if remaining_tokens <= 0 and preserve_system:
            # Situazione critica: tronca i messaggi di sistema
            truncated_system = []
            remaining_tokens = max_tokens - 2
            
            for msg in system_messages:
                content = msg["content"]
                token_count = self.count_tokens(content) + 4
                
                if token_count <= remaining_tokens:
                    truncated_system.append(msg)
                    remaining_tokens -= token_count
                else:
                    # Tronca il contenuto
                    while token_count > remaining_tokens and len(content) > 0:
                        content = content[:int(0.8 * len(content))]  # Riduci del 20%
                        token_count = self.count_tokens(content) + 4
                    
                    if len(content) > 0:
                        truncated_system.append({"role": "system", "content": content})
                        remaining_tokens -= token_count
            
            system_messages = truncated_system
        
        # Se ancora non c'è spazio, non possiamo fare nulla
        if remaining_tokens <= 0:
            return system_messages if preserve_system else []
        
        # Ora adatta gli altri messaggi allo spazio rimanente
        truncated_others = []
        
        # Parti dagli ultimi messaggi (più recenti)
        for msg in reversed(other_messages):
            content = msg["content"]
            token_count = self.count_tokens(content) + 4
            
            if token_count <= remaining_tokens:
                truncated_others.insert(0, msg)  # Inserisci all'inizio per mantenere l'ordine
                remaining_tokens -= token_count
            else:
                # Se è l'ultimo messaggio utente, prova a troncarlo anziché scartarlo
                if msg["role"] == "user" and len(truncated_others) == 0:
                    # Tronca il contenuto
                    while token_count > remaining_tokens and len(content) > 10:
                        content = content[:int(0.8 * len(content))]  # Riduci del 20%
                        token_count = self.count_tokens(content) + 4
                    
                    if token_count <= remaining_tokens:
                        truncated_others.insert(0, {"role": msg["role"], "content": content + " [truncated]"})
                        remaining_tokens -= token_count
                
                # Se non c'è più spazio, interrompi
                if remaining_tokens <= 0:
                    break
        
        # Combina i messaggi di sistema con gli altri
        return system_messages + truncated_others
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Genera un embedding per un testo
        
        Args:
            text: Testo da convertire in embedding
        
        Returns:
            Vettore di embedding
        """
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Errore nella generazione dell'embedding: {e}")
            return []


if __name__ == "__main__":
    # Esempio di utilizzo
    from dotenv import load_dotenv
    load_dotenv()
    
    client = OpenAIClient()
    
    # Test di generazione di una risposta
    messages = [
        {"role": "system", "content": "You are a helpful assistant specialized in emergency management."},
        {"role": "user", "content": "What are the main phases of emergency management?"}
    ]
    
    print("Generating response...")
    response = client.generate_response(messages)
    print(f"Response: {response}\n")
    
    # Test del conteggio di token
    text = "This is a sample text to count tokens in the OpenAI API."
    token_count = client.count_tokens(text)
    print(f"Token count for text: {token_count}")
    
    message_tokens = client.count_messages_tokens(messages)
    print(f"Token count for messages: {message_tokens}\n")
    
    # Test della troncatura dei messaggi
    long_messages = [
        {"role": "system", "content": "You are a helpful assistant specialized in emergency management."},
        {"role": "user", "content": "Tell me about emergency management."},
        {"role": "assistant", "content": "Emergency management is the organization and management of resources and responsibilities for dealing with all humanitarian aspects of emergencies. It involves preparedness, response, recovery, and mitigation."},
        {"role": "user", "content": "What about the phases?"},
        {"role": "assistant", "content": "The four phases of emergency management are:\n1. Mitigation\n2. Preparedness\n3. Response\n4. Recovery"},
        {"role": "user", "content": "Can you elaborate on each phase with examples?" * 20}  # Messaggio lungo
    ]
    
    truncated = client.truncate_messages_to_fit_context(long_messages, max_tokens=1000)
    print(f"Original messages: {len(long_messages)}")
    print(f"Truncated messages: {len(truncated)}")
    print(f"Truncated token count: {client.count_messages_tokens(truncated)}")