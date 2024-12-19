from pinecone import Pinecone
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_base_url = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_deployment = "gpt-4o"  # Azure GPT-4o deployment name

# Initialize Pinecone and Azure OpenAI clients
pc = Pinecone(api_key=pinecone_api_key)
index_name = "knowledge-base"
namespace = "markdown_chunks"

index = pc.Index(index_name)
azure_openai_client = AzureOpenAI(
    api_key=azure_api_key,
    api_version=azure_api_version,
    azure_endpoint=azure_base_url,
    azure_deployment=azure_deployment
)


def load_system_prompt(file_path="instructions.txt"):
    """Load the system prompt from a text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"System prompt file '{file_path}' not found.")
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read().strip()


def generate_query_embedding(user_query):
    """Generate query embeddings using Pinecone's inference model."""
    embeddings = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[user_query],  # User's query
        parameters={"input_type": "passage"}
    )
    return embeddings[0]["values"]  # Extract the embedding vector

def search_pinecone(query_embedding, top_k=3):
    """Query Pinecone to retrieve relevant chunks with full metadata."""
    results = index.query(
        namespace=namespace,
        vector=query_embedding,
        top_k=top_k,
        include_values=False,  # We don't need embedding values for the response
        include_metadata=True  # Include metadata for context enrichment
    )

    # Handle missing or incomplete metadata safely
    return [
        {
            "text": match['metadata'].get('text', '[Missing text]'),
            "section": match['metadata'].get('section', 'Unknown Section'),
            "file": match['metadata'].get('file', 'Unknown File')
        }
        for match in results.get('matches', [])
    ]

def ask_gpt_with_context(user_query, context, system_prompt):
    """Send the user query with retrieved context to Azure GPT."""
    combined_system_prompt = f"{system_prompt}\n\nContext:\n{context}"

    # Debugging: Print the extracted context
    print("\n[DEBUG] Retrieved Context:")
    print("-------------------------")
    print(context)
    print("-------------------------\n")

    # Send the query and context to Azure GPT
    response = azure_openai_client.chat.completions.create(
        model=azure_deployment,
        messages=[
            {"role": "system", "content": combined_system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

def chat_with_knowledge_base(user_query, system_prompt):
    """Main function to handle the user query."""
    print("Generating query embedding...")
    query_embedding = generate_query_embedding(user_query)

    print("Searching Pinecone for relevant context...")
    relevant_chunks = search_pinecone(query_embedding)

    if not relevant_chunks:
        print("No relevant chunks found in Pinecone.")
        return "I'm sorry, I couldn't find relevant information in the knowledge base."

    # Build context with metadata
    context_parts = [
        f"Section: {chunk['section']}\nFile: {chunk['file']}\n\n{chunk['text']}"
        for chunk in relevant_chunks
    ]
    context = "\n\n---\n\n".join(context_parts)  # Separate chunks with a divider

    print("Sending context and query to GPT...")
    gpt_response = ask_gpt_with_context(user_query, context, system_prompt)

    return gpt_response

if __name__ == "__main__":
    try:
        # Load the system prompt
        system_prompt = load_system_prompt()

        print("Welcome to the Knowledge Base Chat!")
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            response = chat_with_knowledge_base(user_input, system_prompt)
            print(f"GPT-4o: {response}")
    except Exception as e:
        print(f"Error: {e}")