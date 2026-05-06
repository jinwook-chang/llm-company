import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Load .env from rag_vault directory or root
load_dotenv()

PROVIDER = os.getenv("PROVIDER") or os.getenv("LLM_WIKI_PROVIDER") or "vertex"
PROVIDER = PROVIDER.lower()

def get_model(deployment_name=None, user_id=None, settings=None):
    if user_id is None:
        user_id = os.getenv("AZURE_OPENAI_USER") or "default_user"
    
    if PROVIDER == "vertex":
        model_name = deployment_name or os.getenv("VERTEX_AI_MODEL") or os.getenv("VERTEX_MODEL") or "gemini-1.5-flash"
        return ChatGoogleGenerativeAI(
            model=model_name,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
            vertexai=True,
            streaming=True
        )
    else:
        # Default to Azure
        if deployment_name is None:
            deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
            
        return AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_deployment=deployment_name,
            default_headers={
                "x-samsung-bda-purpose": os.getenv("AZURE_OPENAI_PURPOSE"),
                "x-samsung-bda-user": user_id,
            },
            streaming=True,
            use_responses_api=True
        )

def get_embeddings():
    if PROVIDER == "vertex":
        return GoogleGenerativeAIEmbeddings(
            model=os.getenv("VERTEX_AI_EMBEDDING_MODEL") or os.getenv("VERTEX_EMBEDDING_MODEL") or "text-multilingual-embedding-002",
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
            vertexai=True
        )
    else:
        # Default to Azure
        return AzureOpenAIEmbeddings(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
            default_headers={
                "x-samsung-bda-purpose": os.getenv("AZURE_OPENAI_PURPOSE"),
                "x-samsung-bda-user": os.getenv("AZURE_OPENAI_USER"),
            }
        )
