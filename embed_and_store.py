from pinecone import Pinecone, ServerlessSpec
import re
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")

# Initialize Pinecone client
pc = Pinecone(api_key=pinecone_api_key)

# Index configuration
INDEX_NAME = "knowledge-base"
NAMESPACE = "markdown_chunks"
DIMENSION = 1024  # Dimension for multilingual-e5-large
PINECONE_CLOUD = "aws"  # Replace with your cloud provider
PINECONE_REGION = "us-east-1"  # Replace with your region


def ensure_index_exists(index_name, dimension, cloud, region):
    """Ensure the Pinecone index exists; create if it doesn't."""
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating index '{index_name}' with dimension {dimension}...")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec=ServerlessSpec(cloud=cloud, region=region)
        )
        print(f"Index '{index_name}' created successfully.")
    else:
        print(f"Index '{index_name}' already exists. Skipping creation.")


def delete_namespace_vectors(index_name, namespace):
    """Deletes all vectors in the specified namespace."""
    index = pc.Index(index_name)
    print(f"Deleting all vectors in namespace '{namespace}'...")
    index.delete(delete_all=True, namespace=namespace)
    print(f"Namespace '{namespace}' cleared.")


def split_markdown_into_chunks_with_metadata(file_path, chunk_size=2800, overlap=200):
    """Splits markdown content into chunks with metadata, adding overlap only for long H1 sections."""
    with open(file_path, "r", encoding="utf-8") as file:
        markdown_content = file.read()

    # Split content by H1 headings
    sections = re.split(r'(?=\n# )', markdown_content)
    processed_chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract the H1 title as metadata
        section_title = section.split("\n")[0].strip()  # The first line is the H1 title

        # If section is small enough, add it as is
        if len(section) <= chunk_size:
            processed_chunks.append({"text": section, "metadata": {"section": section_title, "file": file_path}})
        else:
            # Split large sections with overlap
            start = 0
            while start < len(section):
                end = min(start + chunk_size, len(section))
                chunk = section[start:end]

                # Avoid cutting mid-word
                if end < len(section):
                    last_space = chunk.rfind(" ")
                    if last_space != -1:
                        end = start + last_space

                processed_chunks.append({
                    "text": section[start:end].strip(),
                    "metadata": {"section": section_title, "file": file_path}
                })
                start = end - overlap if end < len(section) else len(section)

    return processed_chunks

def embed_and_store_with_pinecone(file_path, index_name, namespace):
    """Embeds markdown chunks and stores them in Pinecone."""
    index = pc.Index(index_name)

    # Extract the file name from the file path
    file_name = file_path.split("/")[-1]

    # Split markdown content with metadata
    chunks_with_metadata = split_markdown_into_chunks_with_metadata(file_path)
    print(f"Processing {len(chunks_with_metadata)} chunks...")

    # Generate embeddings using Pinecone's inference API
    embeddings = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[chunk["text"] for chunk in chunks_with_metadata],
        parameters={"input_type": "passage"}
    )

    # Prepare vectors for Pinecone and ensure 'text' is part of the metadata
    vectors = []
    for idx, (chunk, embedding) in enumerate(zip(chunks_with_metadata, embeddings)):
        metadata = chunk["metadata"]
        metadata["text"] = chunk["text"]  # Explicitly add text to metadata
        metadata["file"] = file_name  # Add the file name to metadata
        vectors.append({
            "id": f"{file_name}_chunk_{idx}",  # Make ID unique by including the file name
            "values": embedding["values"],
            "metadata": metadata
        })

    # Upsert vectors into Pinecone
    print(f"Upserting {len(vectors)} embeddings into Pinecone (namespace: {namespace})...")
    index.upsert(vectors=vectors, namespace=namespace)
    print("Chunks embedded and stored successfully in Pinecone.")

if __name__ == "__main__":
    # Ensure the Pinecone index exists
    ensure_index_exists(INDEX_NAME, DIMENSION, PINECONE_CLOUD, PINECONE_REGION)
    try:
        # Delete existing vectors in the namespace only if starting fresh
        delete_namespace_vectors(INDEX_NAME, NAMESPACE)  # Comment out or remove this if you don't want to clear existing data
        time.sleep(10)
    except:
        print('Nothing to delete!')

    # Process and store embeddings for the markdown files
    file_paths = ["tucuvi_data_organizational.md", "tucuvi_data_technical.md"]
    for file_path in file_paths:
        embed_and_store_with_pinecone(file_path, INDEX_NAME, NAMESPACE)