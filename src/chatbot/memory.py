from typing import List, Dict, Any, Optional
import json
import os
import time

class Message:
    """Rappresenta un messaggio nella conversazione"""
    
    def __init__(self, role: str, content: str, timestamp: float = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte il messaggio in un dizionario"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Crea un messaggio da un dizionario"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time())
        )
    
    def to_openai_format(self) -> Dict[str, str]:
        """Formatta il messaggio per l'API OpenAI"""
        return {
            "role": self.role,
            "content": self.content
        }


class ConversationMemory:
    """Gestisce la memoria della conversazione per il chatbot"""
    
    def __init__(self, max_messages: int = 50):
        self.messages: List[Message] = []
        self.max_messages = max_messages
    
    def add_message(self, role: str, content: str) -> None:
        """Aggiunge un messaggio alla conversazione"""
        message = Message(role, content)
        self.messages.append(message)
        
        # Tronca la storia se supera la lunghezza massima
        if len(self.messages) > self.max_messages:
            # Mantieni sempre il sistema e gli ultimi (max_messages - 1) messaggi
            system_messages = [m for m in self.messages if m.role == "system"]
            other_messages = [m for m in self.messages if m.role != "system"]
            other_messages = other_messages[-(self.max_messages - len(system_messages)):]
            self.messages = system_messages + other_messages
    
    def get_messages(self, include_system: bool = True) -> List[Message]:
        """Ottiene tutti i messaggi della conversazione"""
        if include_system:
            return self.messages
        else:
            return [m for m in self.messages if m.role != "system"]
    
    def get_last_n_messages(self, n: int, include_system: bool = False) -> List[Message]:
        """Ottiene gli ultimi n messaggi della conversazione"""
        messages = self.get_messages(include_system)
        return messages[-n:] if n < len(messages) else messages
    
    def get_openai_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """Ottiene i messaggi nel formato richiesto dall'API OpenAI"""
        return [m.to_openai_format() for m in self.get_messages(include_system)]
    
    def clear(self, keep_system: bool = True) -> None:
        """Cancella la memoria della conversazione"""
        if keep_system:
            self.messages = [m for m in self.messages if m.role == "system"]
        else:
            self.messages = []
    
    def set_system_message(self, content: str) -> None:
        """Imposta o aggiorna il messaggio di sistema"""
        # Rimuovi eventuali messaggi di sistema esistenti
        self.messages = [m for m in self.messages if m.role != "system"]
        
        # Aggiungi il nuovo messaggio di sistema all'inizio
        system_message = Message("system", content)
        self.messages.insert(0, system_message)
    
    def save_to_file(self, file_path: str) -> None:
        """Salva la conversazione su file"""
        data = {
            "messages": [m.to_dict() for m in self.messages]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, file_path: str) -> bool:
        """Carica la conversazione da file"""
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.messages = [Message.from_dict(m) for m in data.get("messages", [])]
            return True
        except Exception as e:
            print(f"Errore nel caricamento della conversazione: {e}")
            return False
    
    def get_summary(self, max_length: int = 200) -> str:
        """Genera un breve riepilogo della conversazione"""
        if not self.messages:
            return "No conversation history."
        
        # Conta i messaggi per ruolo
        user_count = sum(1 for m in self.messages if m.role == "user")
        assistant_count = sum(1 for m in self.messages if m.role == "assistant")
        
        # Prendi l'ultimo messaggio utente e assistente
        last_user = next((m.content for m in reversed(self.messages) if m.role == "user"), "")
        last_assistant = next((m.content for m in reversed(self.messages) if m.role == "assistant"), "")
        
        # Tronca i contenuti se necessario
        if len(last_user) > max_length:
            last_user = last_user[:max_length] + "..."
        if len(last_assistant) > max_length:
            last_assistant = last_assistant[:max_length] + "..."
        
        return (
            f"Conversation with {user_count} user messages and {assistant_count} assistant responses.\n"
            f"Last user: \"{last_user}\"\n"
            f"Last assistant: \"{last_assistant}\""
        )


if __name__ == "__main__":
    # Esempio di utilizzo
    memory = ConversationMemory()
    
    # Imposta il messaggio di sistema
    memory.set_system_message("You are a helpful assistant specialized in emergency management.")
    
    # Aggiungi alcuni messaggi di esempio
    memory.add_message("user", "Can you help me understand the SVA framework?")
    memory.add_message("assistant", "The SVA (Structural Vulnerability Assessment) framework is a methodology for assessing and managing risks in urban environments and public events.")
    memory.add_message("user", "What are the key components?")
    
    # Ottieni i messaggi nel formato OpenAI
    openai_messages = memory.get_openai_messages()
    print("OpenAI Format Messages:")
    for msg in openai_messages:
        print(f"{msg['role']}: {msg['content'][:50]}...")
    
    # Salva e carica la conversazione
    memory.save_to_file("conversation.json")
    
    new_memory = ConversationMemory()
    new_memory.load_from_file("conversation.json")
    print("\nLoaded Conversation Summary:")
    print(new_memory.get_summary())