import os
import glob
import PyPDF2
import re
import json
from typing import List, Dict, Any, Optional
import numpy as np
from openai import OpenAI
import tiktoken

class Document:
    """Classe per rappresentare un documento con testo e metadati"""
    
    def __init__(self, text: str, metadata: Dict[str, Any] = None):
        self.text = text
        self.metadata = metadata or {}
        self.embedding = None
    
    def __str__(self):
        return f"Document(text='{self.text[:50]}...', metadata={self.metadata})"


class DocumentStore:
    """Gestisce l'archiviazione e il recupero di documenti per il chatbot"""
    
    def __init__(self, client: OpenAI, embedding_model: str = "text-embedding-ada-002"):
        self.client = client
        self.embedding_model = embedding_model
        self.documents = []
        self.embeddings = []
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Encoding per i modelli OpenAI
    
    def add_document(self, document: Document) -> None:
        """Aggiunge un documento allo store e calcola l'embedding"""
        try:
            # Calcola l'embedding per il documento
            embedding = self._get_embedding(document.text)
            document.embedding = embedding
            
            # Aggiungi il documento allo store
            self.documents.append(document)
            self.embeddings.append(embedding)
            
            print(f"Documento aggiunto: {document.metadata.get('source', 'Sconosciuto')}")
        except Exception as e:
            print(f"Errore nell'aggiunta del documento: {e}")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Ottiene l'embedding per un testo usando l'API OpenAI"""
        # Tronca il testo se necessario per rispettare i limiti dell'API
        max_tokens = 8191  # Limite per text-embedding-ada-002
        tokens = self.tokenizer.encode(text)
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]
            text = self.tokenizer.decode(tokens)
        
        # Ottieni l'embedding
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        
        # Estrai il vettore di embedding
        embedding = response.data[0].embedding
        return np.array(embedding)
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcola la similarità del coseno tra due vettori"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def search(self, query: str, top_k: int = 5) -> List[Document]:
        """Cerca i documenti più rilevanti per una query"""
        if not self.documents:
            print("Nessun documento nello store.")
            return []
        
        try:
            # Calcola l'embedding per la query
            query_embedding = self._get_embedding(query)
            
            # Calcola le similarità con tutti i documenti
            similarities = [
                self._cosine_similarity(query_embedding, doc.embedding)
                for doc in self.documents
            ]
            
            # Ordina i documenti per similarità
            sorted_indices = np.argsort(similarities)[::-1]
            top_indices = sorted_indices[:top_k]
            
            # Restituisci i documenti più rilevanti
            return [self.documents[i] for i in top_indices]
        except Exception as e:
            print(f"Errore nella ricerca: {e}")
            return []
    
    def load_documents_from_directory(self, directory: str, source_type: str = "unknown") -> None:
        """Carica documenti da una directory"""
        if not os.path.exists(directory):
            print(f"La directory {directory} non esiste.")
            return
        
        try:
            # Cerca file PDF
            pdf_files = glob.glob(os.path.join(directory, "*.pdf"))
            for pdf_file in pdf_files:
                documents = self._extract_text_from_pdf(pdf_file, source_type)
                for doc in documents:
                    self.add_document(doc)
            
            # Cerca file di testo
            text_files = glob.glob(os.path.join(directory, "*.txt"))
            text_files += glob.glob(os.path.join(directory, "*.md"))
            for text_file in text_files:
                documents = self._extract_text_from_file(text_file, source_type)
                for doc in documents:
                    self.add_document(doc)
            
            print(f"Caricati {len(self.documents)} documenti da {directory}")
        except Exception as e:
            print(f"Errore nel caricamento dei documenti: {e}")
    
    def _extract_text_from_pdf(self, pdf_path: str, source_type: str) -> List[Document]:
        """Estrae testo da un file PDF e lo divide in chunks"""
        documents = []
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"
                
                # Dividi il testo in chunks di dimensione gestibile
                chunks = self._split_text(text)
                
                # Crea un documento per ogni chunk
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        text=chunk,
                        metadata={
                            "source": os.path.basename(pdf_path),
                            "source_type": source_type,
                            "chunk_id": i
                        }
                    )
                    documents.append(doc)
        except Exception as e:
            print(f"Errore nell'estrazione del testo da {pdf_path}: {e}")
        
        return documents
    
    def _extract_text_from_file(self, file_path: str, source_type: str) -> List[Document]:
        """Estrae testo da un file di testo e lo divide in chunks"""
        documents = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
                
                # Dividi il testo in chunks di dimensione gestibile
                chunks = self._split_text(text)
                
                # Crea un documento per ogni chunk
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        text=chunk,
                        metadata={
                            "source": os.path.basename(file_path),
                            "source_type": source_type,
                            "chunk_id": i
                        }
                    )
                    documents.append(doc)
        except Exception as e:
            print(f"Errore nell'estrazione del testo da {file_path}: {e}")
        
        return documents
    
    def _split_text(self, text: str, max_tokens: int = 1000, overlap: int = 200) -> List[str]:
        """Divide il testo in chunks di dimensione appropriata"""
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        # Dividi i token in chunks con sovrapposizione
        i = 0
        while i < len(tokens):
            # Prendi un chunk di token
            end = min(i + max_tokens, len(tokens))
            chunk_tokens = tokens[i:end]
            
            # Converti i token in testo
            chunk = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk)
            
            # Avanza di (max_tokens - overlap) token
            i += max_tokens - overlap
            if i >= len(tokens):
                break
        
        return chunks
    
    def get_context_for_query(self, query: str, max_tokens: int = 3000) -> str:
        """Ottiene un contesto rilevante per la query"""
        relevant_docs = self.search(query)
        
        if not relevant_docs:
            return ""
        
        # Combina i documenti più rilevanti in un unico contesto
        context = ""
        total_tokens = 0
        
        for doc in relevant_docs:
            doc_tokens = self.tokenizer.encode(doc.text)
            if total_tokens + len(doc_tokens) > max_tokens:
                # Se aggiungere il documento supera il limite di token, salta
                continue
            
            # Aggiungi il documento al contesto
            source_info = f"\nFonte: {doc.metadata.get('source', 'Sconosciuta')}\n"
            context += source_info + doc.text + "\n\n"
            total_tokens += len(doc_tokens) + len(self.tokenizer.encode(source_info))
        
        return context.strip()
    
    def save_to_file(self, file_path: str) -> None:
        """Salva i documenti su file per uso futuro"""
        data = []
        for doc in self.documents:
            data.append({
                "text": doc.text,
                "metadata": doc.metadata,
                "embedding": doc.embedding.tolist() if doc.embedding is not None else None
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Documenti salvati in {file_path}")
    
    def load_from_file(self, file_path: str) -> None:
        """Carica documenti da file"""
        if not os.path.exists(file_path):
            print(f"Il file {file_path} non esiste.")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.documents = []
            self.embeddings = []
            
            for item in data:
                doc = Document(text=item["text"], metadata=item["metadata"])
                if item["embedding"]:
                    doc.embedding = np.array(item["embedding"])
                    self.embeddings.append(doc.embedding)
                self.documents.append(doc)
            
            print(f"Caricati {len(self.documents)} documenti da {file_path}")
        except Exception as e:
            print(f"Errore nel caricamento dei documenti da file: {e}")


if __name__ == "__main__":
    # Esempio di utilizzo
    from dotenv import load_dotenv
    load_dotenv()
    
    client = OpenAI()
    store = DocumentStore(client)
    
    # Carica documenti da directory
    store.load_documents_from_directory("./docs/sva_framework", "sva_framework")
    store.load_documents_from_directory("./docs/gorizia_event", "gorizia_event")
    
    # Salva i documenti su file
    store.save_to_file("documents.json")
    
    # Test di ricerca
    query = "What security measures are recommended for public events?"
    context = store.get_context_for_query(query)
    print(f"Context for query '{query}':\n{context}")