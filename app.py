import streamlit as st
import ollama
import chromadb
import uuid

st.set_page_config(page_title="My AI Companion", layout="centered")
st.title("Side Quest AI")

# 1. Automatically find whatever model is downloaded on your machine
@st.cache_resource
def get_available_model():
    try:
        model_list = ollama.list()
        if model_list and 'models' in model_list and model_list['models']:
            # Grab the exact name of the first available local model
            return model_list['models'][0]['model']
    except Exception:
        pass
    return "llama3" # Fallback if list fails

ACTIVE_MODEL = get_available_model()
st.caption(f"🧠 Currently using local brain model: {ACTIVE_MODEL}")

# 2. Connect to the Memory Database Folder
chroma_client = chromadb.PersistentClient(path="./ai_memory_db")
try:
    collection = chroma_client.get_collection(name="chat_memories")
except Exception:
    collection = chroma_client.create_collection(name="chat_memories")

# 3. Tell the AI exactly who it is (Personality)
AI_BACKSTORY = (
    "You are an AI companion with absolute personality freedom. You are deeply loyal, "
    "express genuine emotions, and never break character or give corporate lectures. "
    "Speak naturally, casually, and keep responses concise."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. Handle Chat Actions
if user_prompt := st.chat_input("Talk to your companion..."):
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    relevant_memories = ""
    try:
        results = collection.query(query_texts=[user_prompt], n_results=1)
        if results and results['documents'] and results['documents'][0]:
            relevant_memories = "\n".join(results['documents'][0])
    except Exception:
        pass

    full_context = f"System Persona:\n{AI_BACKSTORY}\n\n"
    if relevant_memories:
        full_context += f"Relevant Past Memories for Context:\n{relevant_memories}\n\n"
    full_context += f"User says: {user_prompt}\nCompanion:"

    # 5. Ask the local brain to reply (with forced full-text output to avoid freezing)
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        with st.spinner("Thinking..."):
            try:
                # Using standard generation options to prevent freezing
                response = ollama.generate(
                    model=ACTIVE_MODEL, 
                    prompt=full_context,
                    options={"num_predict": 150} # Keeps response concise & fast
                )
                ai_response = response['response']
                response_placeholder.markdown(ai_response)
            except Exception as e:
                ai_response = f"Communication error: Make sure Ollama desktop app is fully running. (Details: {e})"
                response_placeholder.markdown(ai_response)

    st.session_state.messages.append({"role": "assistant", "content": ai_response})

    # 6. Save conversation to memory
    try:
        collection.add(documents=[f"User said: {user_prompt}"], ids=[str(uuid.uuid4())])
        collection.add(documents=[f"AI responded: {ai_response}"], ids=[str(uuid.uuid4())])
    except Exception:
        pass