import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from utils import get_embeddings

def debug_embeddings():
    print("Initializing embeddings...")
    embeddings_model = get_embeddings()
    
    test_texts = ["Hello world", "This is a test document"]
    print(f"Testing with {len(test_texts)} documents.")
    
    # Try with a standard model name
    print("\n--- Trying with text-multilingual-embedding-002 ---")
    try:
        temp_model = GoogleGenerativeAIEmbeddings(
            model="text-multilingual-embedding-002",
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
            vertexai=True
        )
        embeddings = temp_model.embed_documents(test_texts)
        print(f"Length of result: {len(embeddings)}")
    except Exception as e:
        print(f"Error: {e}")
        
        print("\n--- Result Analysis ---")
        print(f"Type of result: {type(embeddings)}")
        print(f"Length of result: {len(embeddings)}")
        
        if len(embeddings) > 0:
            first_element = embeddings[0]
            print(f"Type of first element: {type(first_element)}")
            if hasattr(first_element, "__len__"):
                print(f"Length of first element (vector size): {len(first_element)}")
            else:
                print(f"First element: {first_element}")
                
        if len(embeddings) != len(test_texts):
            print(f"\n❌ MISMATCH: Expected {len(test_texts)} embeddings, but got {len(embeddings)}.")
            if len(embeddings) == 1:
                print("The model seems to be collapsing the batch into a single output.")
        else:
            print("\n✅ Match: Lengths are correct.")
            
    except Exception as e:
        print(f"❌ Error during embedding: {e}")

if __name__ == "__main__":
    debug_embeddings()
