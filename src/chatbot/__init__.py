# Import the main class so it's available when importing the package
from chatbot.chatbot_main import SafeCitiesChatbot

# Import other classes for convenience
from chatbot.openai_client import OpenAIClient
from chatbot.document_store import DocumentStore, Document
from chatbot.memory import ConversationMemory, Message
from chatbot.simulation import SimulationEngine

# Define what's available when importing the package
__all__ = [
    'SafeCitiesChatbot',
    'OpenAIClient',
    'DocumentStore',
    'Document',
    'ConversationMemory',
    'Message',
    'SimulationEngine'
]
