This repository is designed to embed documents in Pinecone and enable conversational interactions with the embedded data.

---

## Features

### 1. Document Embedding in Pinecone

- **Document Splitting**:Split large documents into relevant chunks for better context retrieval.
- **Embedding Creation**:Generate embeddings for each chunk and store them in Pinecone for efficient similarity searches.

### 2. Interactive Chat for Document Queries

- **Context-based Chat**:Users can interact with the embedded documents in two contexts:
    - **Organizational Context**: Default interaction mode.
    - **Technical Context**: Activated with the `/tech` command.
- **Query Retrieval**: Retrieve the **3 most relevant chunks** based on the user query and use them as context for conversation.

---

## Usage

### Document Embedding

1. Prepare the document and split it into chunks based on content relevance.
2. Create embeddings for each chunk using your preferred embedding model.
3. Store the embeddings in Pinecone for efficient retrieval.

### Chat Interaction

1. **Start a Conversation**:Use the chat interface to interact with the documents.
2. **Switch Contexts**:
    - Use `/tech` for technical questions.
    - Use the default mode for organizational queries.
3. **Retrieve Context**:Query Pinecone to fetch the top 3 most relevant chunks for your input. These chunks provide the context for the AI response.