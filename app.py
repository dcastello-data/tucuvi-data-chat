import streamlit as st
from pinecone import Pinecone
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
from google_auth_oauthlib.flow import Flow
import requests

# Load environment variables
load_dotenv()
pinecone_api_key = os.getenv("PINECONE_API_KEY")
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_base_url = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_deployment = "gpt-4o"

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI_LOCAL = "http://localhost:8501"
REDIRECT_URI = "https://chat-tucuvi-data.streamlit.app"

# Google Auth Flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI, REDIRECT_URI_LOCAL],
        }
    },
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"],
)

INDEX_NAME = "knowledge-base"
NAMESPACE = "markdown_chunks"
DIMENSION = 1024
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"

pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(INDEX_NAME)
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
    """Generate query embeddings using Pinecone."""
    embeddings = pc.inference.embed(
        model="multilingual-e5-large",
        inputs=[user_query],
        parameters={"input_type": "passage"}
    )
    return embeddings[0]["values"]

def search_pinecone(query_embedding, knowledge_file, top_k=3):
    """Query Pinecone for relevant chunks."""
    results = index.query(
        namespace=NAMESPACE,
        vector=query_embedding,
        top_k=top_k,
        include_values=False,
        include_metadata=True,
        filter={"file": knowledge_file}
    )
    return [
        {
            "text": match['metadata'].get('text', '[Missing text]'),
            "section": match['metadata'].get('section', 'Unknown Section'),
            "file": match['metadata'].get('file', 'Unknown File')
        }
        for match in results.get('matches', [])
    ]

def ask_gpt(messages):
    """Send messages to Azure OpenAI Chat."""
    response = azure_openai_client.chat.completions.create(
        model=azure_deployment,
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content

def determine_context_type(prompt):
    if prompt.startswith("/tech"):
        cleaned_prompt = prompt.replace("/tech", "").strip()
        return "tucuvi_data_technical.md", cleaned_prompt, "system_prompts/instructions_tech.txt"
    else:
        return "tucuvi_data_organizational.md", prompt.strip(), "system_prompts/instructions.txt"

def build_messages_with_context(system_prompt, conversation_history, context, user_query):
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history:
        messages.append(msg)
    messages.append({"role": "assistant", "content": f"Context:\n{context}"})
    messages.append({"role": "user", "content": user_query})
    return messages

def get_last_interactions(messages, user_turns=2, assistant_turns=2):
    # Extract the last user_assistant messages for history
    last_interactions = []
    reversed_messages = list(reversed(messages))
    user_count = 0
    assistant_count = 0
    for msg in reversed_messages:
        if msg["role"] == "assistant" and assistant_count < assistant_turns:
            last_interactions.insert(0, msg)
            assistant_count += 1
        elif msg["role"] == "user" and user_count < user_turns:
            last_interactions.insert(0, msg)
            user_count += 1
        if user_count == user_turns and assistant_count == assistant_turns:
            break
    return last_interactions

def process_new_thread(user_input):
    """Handle starting a new thread."""
    if not user_input.strip():
        st.session_state.messages.append(
            {"role": "assistant", "content": "Please provide a valid query to start a new thread."}
        )
        return

    # Reset session state for a new thread
    st.session_state.messages = []
    st.session_state.knowledge_file = None
    st.session_state.system_prompt = None
    st.session_state.context_chunks = []

    # Retrieve knowledge file, cleaned query, and instructions
    knowledge_file, cleaned_query, instructions_file = determine_context_type(user_input)
    st.session_state.knowledge_file = knowledge_file
    st.session_state.system_prompt = load_system_prompt(file_path=instructions_file)

    # Generate embeddings and search for relevant context
    query_embedding = generate_query_embedding(cleaned_query)
    relevant_chunks = search_pinecone(query_embedding, knowledge_file)

    if not relevant_chunks:
        response = "I'm sorry, I couldn't find relevant information."
        st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        context_parts = [
            f"Section: {chunk['section']}\nFile: {chunk['file']}\n\n{chunk['text']}"
            for chunk in relevant_chunks
        ]
        context = "\n\n---\n\n".join(context_parts)

        # Generate the assistant's response
        messages = build_messages_with_context(
            st.session_state.system_prompt, [], context, cleaned_query
        )
        response = ask_gpt(messages)

        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.context_chunks = relevant_chunks

def process_continue_thread(user_input):
    """Handle continuing an existing thread."""
    if not st.session_state.system_prompt or not st.session_state.knowledge_file:
        st.session_state.messages.append(
            {"role": "assistant", "content": "No active thread found. Please start a new thread."}
        )
        return

    if not user_input.strip():
        st.session_state.messages.append(
            {"role": "assistant", "content": "Please provide a valid query to continue the thread."}
        )
        return

    st.session_state.messages.append({"role": "user", "content": user_input})

    last_interactions = get_last_interactions(st.session_state.messages)

    if not st.session_state.context_chunks:
        context = "No previous context available."
    else:
        context_parts = [
            f"Section: {chunk['section']}\nFile: {chunk['file']}\n\n{chunk['text']}"
            for chunk in st.session_state.context_chunks
        ]
        context = "\n\n---\n\n".join(context_parts)

    messages = build_messages_with_context(
        st.session_state.system_prompt,
        last_interactions,
        context,
        user_input
    )
    response = ask_gpt(messages)

    st.session_state.messages.append({"role": "assistant", "content": response})

def process_continue_thread_update(user_input):
    """Handle continuing an existing thread and updating the knowledge base."""

    # Retrieve knowledge file, cleaned query, and instructions
    knowledge_file, cleaned_query, instructions_file = determine_context_type(user_input)
    st.session_state.knowledge_file = knowledge_file
    st.session_state.system_prompt = load_system_prompt(file_path=instructions_file)

    # Generate embeddings and search for relevant context
    query_embedding = generate_query_embedding(cleaned_query)
    relevant_chunks = search_pinecone(query_embedding, knowledge_file)

    # Handle empty input
    if not user_input.strip():
        st.session_state.messages.append(
            {"role": "assistant", "content": "Please provide a valid query to continue the thread and update the knowledge base."}
        )
        return

    if not relevant_chunks:
        st.session_state.messages.append(
            {"role": "assistant", "content": "No updated information found in the knowledge base for the given query."}
        )
        return

    # Prepare updated context
    context_parts = [
        f"Section: {chunk['section']}\nFile: {chunk['file']}\n\n{chunk['text']}"
        for chunk in relevant_chunks
    ]
    context = "\n\n---\n\n".join(context_parts)

    # Generate the assistant's response
    messages = build_messages_with_context(
        st.session_state.system_prompt,
        get_last_interactions(st.session_state.messages),
        context,
        user_input
    )
    response = ask_gpt(messages)

    # Update context chunks and append the assistant response
    st.session_state.context_chunks = relevant_chunks
    st.session_state.messages.append({"role": "assistant", "content": response})

def auth_page():
    """Authentication Page."""
    st.set_page_config(page_title="Sign In", layout="centered")

        # Load the CSS
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.title("Tucuvi Data Chat")
    st.subheader("Please sign in with Google to continue.")

    # Initialize Google user in session state
    if "google_user" not in st.session_state:
        st.session_state.google_user = None

    # Display Sign-In Button
    if st.session_state.google_user:
        st.success(f"Signed in as: {st.session_state.google_user['name']}")
        st.write(f"Email: {st.session_state.google_user['email']}")
        if st.button("Continue to App"):
            st.session_state.page = "app"
    else:
        flow.redirect_uri = REDIRECT_URI
        auth_url, _ = flow.authorization_url(prompt="consent")

        if st.button("Sign in with Google"):
            st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}" />', unsafe_allow_html=True)

        # Process callback
        if "code" in st.query_params:
            query_params = st.query_params
            flow.fetch_token(authorization_response=query_params["code"][0])
            credentials = flow.credentials
            userinfo_response = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
            userinfo = userinfo_response.json()
            st.session_state.google_user = {
                "name": userinfo.get("name"),
                "email": userinfo.get("email"),
            }
            st.experimental_rerun()

def app_page():
    st.set_page_config(page_title="Knowledge Base Chat", layout="wide")

    # Load the CSS
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    st.markdown("""
        <script>
        document.querySelectorAll('input[type="text"]').forEach(input => {
            input.setAttribute('autocomplete', 'off');
        });
        </script>
        """, unsafe_allow_html=True)
    
    # Create two columns
    col1, col2 = st.columns([1, 2])  # Divide into 1/3 and 2/3 columns
    
    # Title in the first column
    with col1:
        st.markdown("<h1 style='margin-bottom: 0;'>Tucuvi Data</h1>", unsafe_allow_html=True)
    
    # Description in the second column
    with col2:
        st.markdown(
            """
            <p style="font-size: 16px; line-height: 1.6; color: #4A4A4A;">
                When starting a thread, the assistant uses your query to retrieve relevant documentation. To refine or explore further, use 'Continue thread updating knowledge base'. 
                Begin questions with <code>/tech</code> to access technical documentation on Tucuvi Data and signal that your query requires technical insights.
            </p>
            """, 
            unsafe_allow_html=True
        )

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "knowledge_file" not in st.session_state:
        st.session_state.knowledge_file = None
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = None
    if "context_chunks" not in st.session_state:
        st.session_state.context_chunks = []
    if "clear_input_on_next_run" not in st.session_state:
        st.session_state.clear_input_on_next_run = False
    if "action_triggered" not in st.session_state:
        st.session_state.action_triggered = False

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Chat")

        # Buttons
        new_thread_btn = st.button("New thread", key="new_thread_btn")
        continue_thread_btn = st.button("Continue thread")
        continue_thread_update_btn = st.button("Continue thread updating knowledge base")

        user_input = st.text_input(
            "Your message:",
            key="temp_user_input"
        )

        # Clear the input field when the flag is set
        if st.session_state.clear_input_on_next_run:
            st.session_state.clear_input_on_next_run = False

        # Button Logic
        if new_thread_btn:
            st.session_state.action_triggered = True
            process_new_thread(user_input)
            st.session_state.clear_input_on_next_run = True

        elif continue_thread_btn:
            st.session_state.action_triggered = True
            process_continue_thread(user_input)
            st.session_state.clear_input_on_next_run = True

        elif continue_thread_update_btn:
            st.session_state.action_triggered = True
            process_continue_thread_update(user_input)
            st.session_state.clear_input_on_next_run = True

        elif user_input.strip() and not st.session_state.action_triggered:
            # Default behavior: Process input when pressing Enter
            if st.session_state.knowledge_file:
                process_continue_thread(user_input)
            else:
                process_new_thread(user_input)
            st.session_state.clear_input_on_next_run = True

        # Reset action_triggered for the next iteration
        st.session_state.action_triggered = False

        # Display conversation
        for msg in st.session_state.messages:
            with st.container():
                if msg["role"] == "user":
                    st.markdown(
                        f"<div class='user-message'><b>You:</b> {msg['content']}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div class='assistant-message'><b>Assistant:</b> {msg['content']}</div>",
                        unsafe_allow_html=True
                    )

    with col2:
        st.header("Retrieved knowledge")
        if st.session_state.context_chunks:
            for i, chunk in enumerate(st.session_state.context_chunks, start=1):
                # Style for the "Context Chunk" label
                st.markdown(f'<div class="st-chunk-label">Context Chunk {i}:</div>', unsafe_allow_html=True)
                # Style for "Section" detail
                st.markdown(f'<div class="st-chunk-label">- <b>Section:</b> {chunk["section"]}</div>', unsafe_allow_html=True)
                # Style for "File" detail
                st.markdown(f'<div class="st-chunk-label">- <b>File:</b> {chunk["file"]}</div>', unsafe_allow_html=True)
                st.markdown('<div class="st-divider"></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="st-chunk-details">{chunk["text"]}</div>', unsafe_allow_html=True)
                st.markdown('<div class="st-divider"></div>', unsafe_allow_html=True)

def main():
    """Main Function to Handle Page Routing."""
    if "page" not in st.session_state:
        st.session_state.page = "auth"

    if st.session_state.page == "auth":
        auth_page()
    elif st.session_state.page == "app":
        if "google_user" not in st.session_state or not st.session_state.google_user:
            st.session_state.page = "auth"
            st.experimental_rerun()
        app_page()

if __name__ == "__main__":
    main()