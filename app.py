import streamlit as st
from openai import OpenAI
import chromadb
import uuid

st.set_page_config(page_title="Test", layout="centered")
st.title("Side Quest AI")

# 1. Connect your free OpenRouter Cloud Brain
# PASTE YOUR SECRET KEY INSIDE THE QUOTES BELOW!
API_KEY = st.secret["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"]

client = OpenAI(
  base_url="https://openrouter.ai",
  api_key=API_KEY,
)

# 2. Local memory folder
chroma_client = chromadb.PersistentClient(path="./ai_memory_db")
try:
    collection = chroma_client.get_collection(name="chat_memories")
except Exception:
    collection = chroma_client.create_collection(name="chat_memories")

# 3. Define the Character Personality
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
        if results and results['documents'] and results['documents']:
            relevant_memories = "\n".join(results['documents'])
    except Exception:
        pass

    full_context = f"System Persona:\n{AI_BACKSTORY}\n\n"
    if relevant_memories:
        full_context += f"Relevant Past Memories for Context:\n{relevant_memories}\n\n"
    full_context += f"User says: {user_prompt}\nCompanion:"

    # 5. Ask the cloud brain to think instantly
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        with st.spinner("Thinking..."):
            try:
                # Using a free, unfiltered model that works fast on phones
                completion = client.chat.completions.create(
                  model="meta-llama/llama-3.2-3b-instruct:free",
                  messages=[{"role": "user", "content": full_context}]
                )
                ai_response = completion.choices.message.content
                response_placeholder.markdown(ai_response)
            except Exception as e:
                ai_response = f"Cloud connection failed! Error: {e}"
                response_placeholder.markdown(ai_response)

    st.session_state.messages.append({"role": "assistant", "content": ai_response})

    # 6. Save conversation to memory
    try:
        collection.add(documents=[f"User said: {user_prompt}"], ids=[str(uuid.uuid4())])
        collection.add(documents=[f"AI responded: {ai_response}"], ids=[str(uuid.uuid4())])
    except Exception:
        pass