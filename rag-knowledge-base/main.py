import os
import argparse
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.document_loaders import TextLoader, PyPDFLoader
from langchain.schema import Document
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.llms import Ollama
import time

class RAGSystem:
    def __init__(self, persist_directory: str = "./vector_store_ollama", 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 generation_model: str = "llama3:latest"):
        self.persist_directory = persist_directory
        self.vector_store = None
        
        # Pure HuggingFace embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'}
        )
        
        #Ollama LLM
        self.llm = Ollama(model=generation_model)
        self.generation_model = generation_model
        
        print(f"✓ Initialized with {embedding_model} embeddings")
        print(f"✓ Initialized with {generation_model} generation")
        
    def ingest_documents(self, documents_path: str):
        """Ingest documents from directory"""
        documents = []
        
        for filename in os.listdir(documents_path):
            file_path = os.path.join(documents_path, filename)
            
            try:
                if filename.endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                    documents.extend(docs)
                elif filename.endswith('.txt'):
                    loader = TextLoader(file_path, encoding='utf-8')
                    docs = loader.load()
                    documents.extend(docs)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        chunks = text_splitter.split_documents(documents)
        print(f"Created {len(chunks)} chunks from {len(documents)} documents")
        
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        self.vector_store.save_local(self.persist_directory)
        
        return len(chunks)
    
    def load_vector_store(self):
        """Load existing vector store"""
        if os.path.exists(self.persist_directory):
            self.vector_store = FAISS.load_local(
                self.persist_directory, 
                self.embeddings
            )
            return True
        return False
    
    def query(self, question: str, language: str = "en", k: int = 3) -> Dict[str, Any]:
        """Query the knowledge base"""
        if not self.vector_store:
            if not self.load_vector_store():
                return {"error": "Vector store not initialized. Please run --ingest first."}
        
        start_time = time.time()
        
        # Search for relevant documents
        docs = self.vector_store.similarity_search(question, k=k)
        
        # Generate answer using Ollama
        context = "\n\n".join([doc.page_content for doc in docs])
        
        if language == "ar":
            answer = self._generate_arabic_answer(question, context)
        else:
            answer = self._generate_english_answer(question, context)
        
        processing_time = time.time() - start_time
        
        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get('source', 'unknown')
                }
                for doc in docs
            ],
            "processing_time": round(processing_time, 2),
            "embeddings_model": "huggingface",
            "generation_model": self.generation_model
        }
    
    def _generate_english_answer(self, question: str, context: str) -> str:
        """Generate English answer using Ollama"""
        prompt = f"""You are a helpful assistant. Answer the question based ONLY on the provided context.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""
        
        try:
            answer = self.llm.invoke(prompt)
            return answer.strip()
        except Exception as e:
            raise Exception(f"Ollama generation failed: {str(e)}")
    
    def _generate_arabic_answer(self, question: str, context: str) -> str:
        """Generate Arabic answer using Ollama - FORCE Arabic response"""
        prompt = f"""أنت مساعد يتحدث العربية. أجب على السؤال باللغة العربية فقط بناءً على المعلومات المقدمة. لا تستخدم الإنجليزية مطلقاً.

المعلومات:
{context}

السؤال: {question}

الإجابة (يجب أن تكون باللغة العربية فقط):"""
        
        try:
            answer = self.llm.invoke(prompt)
            
            if self._is_arabic(answer):
                return answer.strip()
            else:
                stronger_prompt = f"""أجب باللغة العربية فقط! لا تستخدم الإنجليزية!

المعلومات: {context}

السؤال: {question}

الإجابة (عربي فقط):"""
                arabic_answer = self.llm.invoke(stronger_prompt)
                return arabic_answer.strip()
                
        except Exception as e:
            raise Exception(f"Ollama Arabic generation failed: {str(e)}")
    
    def _is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        arabic_chars = set('ء-ي')  # Arabic Unicode range
        return any(char in arabic_chars for char in text)

def main():
    parser = argparse.ArgumentParser(description="RAG System with Forced Arabic Responses")
    parser.add_argument("--ingest", help="Directory path to ingest documents")
    parser.add_argument("--question", help="Question to ask the knowledge base")
    parser.add_argument("--lang", choices=["en", "ar"], default="en", help="Response language")
    parser.add_argument("--cli", action="store_true", help="Start interactive CLI")
    parser.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2", 
                       help="Hugging Face embedding model to use")
    parser.add_argument("--generation-model", default="llama3:latest", 
                       help="Ollama generation model to use")
    
    args = parser.parse_args()
    
    rag = RAGSystem(
        embedding_model=args.embedding_model,
        generation_model=args.generation_model
    )
    
    if args.ingest:
        chunk_count = rag.ingest_documents(args.ingest)
        print(f"✓ Ingestion complete! Created {chunk_count} chunks.")
        return
    
    if args.question:
        result = rag.query(args.question, args.lang)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Question: {result['question']}")
            print(f"\nAnswer: {result['answer']}")
            source_files = list(set([source['source'] for source in result['sources']]))
            print(f"\nSources: {len(result['sources'])} documents from:")
            for i, source_file in enumerate(source_files, 1):
                print(f"  {i}. {source_file}")
            print(f"Time: {result['processing_time']}s")
            print(f"Embeddings: {result['embeddings_model']}")
            print(f"Generation: {result['generation_model']}")
        return
    
    if args.cli:
        print("RAG Knowledge Base Q&A System")
        print("Commands: 'lang ar' for Arabic, 'lang en' for English, 'quit' to exit")
        
        current_lang = "en"
        while True:
            user_input = input(f"\nQ ({current_lang}): ").strip()
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'lang ar':
                current_lang = 'ar'
                print("Language switched to Arabic")
                continue
            elif user_input.lower() == 'lang en':
                current_lang = 'en'
                print("Language switched to English")
                continue
            elif not user_input: 
                print("Please enter a question or command")
                continue
            
            result = rag.query(user_input, current_lang)
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"\nA: {result['answer']}")
                source_files = list(set([source['source'] for source in result['sources']]))
                source_files_str = ", ".join([os.path.basename(source) for source in source_files])  # Show only filenames
                print(f"\n[Sources: {len(result['sources'])} from: {source_files_str} | Time: {result['processing_time']}s | Models: {result['embeddings_model']}+{result['generation_model']}]")
if __name__ == "__main__":
    main()