import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from glob import glob

load_dotenv()

CHROMA_PATH = "./chroma_db"
DOCUMENTS_PATH = "./data/documents/*.md"

def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

def load_and_split_documents():
    # Mantener la estructura lógica de los documentos fragmentando por encabezados
    headers_to_split_on = [
        ("#", "Category"),
        ("##", "Title"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on, 
        strip_headers=False
    )

    all_docs = []
    for file_path in glob(DOCUMENTS_PATH):
        with open(file_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        
        splits = markdown_splitter.split_text(md_text)
        
        for doc in splits:
            content = doc.page_content
            # Extracción rudimentaria de IDs para meterlos como metadatos vectoriales
            if "**Zabbix Error ID:**" in content:
                z_id = content.split("**Zabbix Error ID:**")[1].split("\n")[0].strip(" `")
                doc.metadata["zabbix_id"] = z_id
            all_docs.append(doc)
    
    return all_docs

def initialize_vector_db():
    embeddings = get_embeddings()
    if not os.path.exists(CHROMA_PATH) or not os.listdir(CHROMA_PATH):
        print("Inicializando la base de datos vectorial con los documentos disponibles...")
        docs = load_and_split_documents()
        vectordb = Chroma.from_documents(
            documents=docs, 
            embedding=embeddings, 
            persist_directory=CHROMA_PATH
        )
    else:
        print("Cargando la base de datos vectorial existente...")
        vectordb = Chroma(
            persist_directory=CHROMA_PATH, 
            embedding_function=embeddings
        )
    return vectordb

from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_google_genai import ChatGoogleGenerativeAI

async def query_rag(query: str, category: str = None):
    vectordb = initialize_vector_db()
    
    search_kwargs = {"k": 3}
    if category:
        search_kwargs["filter"] = {"Category": category}
    base_retriever = vectordb.as_retriever(search_kwargs=search_kwargs)
    
    # Envolvemos el recuperador con MultiQueryRetriever para ganar robustez semántica
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
    retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever, 
        llm=llm
    )
    
    print(f"   [RAG]: Realizando una búsqueda Multi-Query para: '{query}'")
    results = await retriever.ainvoke(query)
    
    # Concatenamos los fragmentos en una string para inyectar en el prompt principal
    context = "\n\n---\n\n".join([doc.page_content for doc in results])
    return context

if __name__ == "__main__":
    # Test query
    print(query_rag("SSD S.M.A.R.T. Failure Prediction"))
