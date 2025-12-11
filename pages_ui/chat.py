import streamlit as st
from chat_agent import process_chat_query

def render():
    
    st.title("💬 AI Financial Assistant")
    st.markdown("Ask questions about your **Spend**, **Vendors**, or **Invoices**. The agent will query the database to answer you.")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Hello! I'm your AI Finance Assistant. You can ask me things like:\n- *Who is our top vendor by spend?*\n- *Show me all invoices from last month.*\n- *Do we have any unapproved POs?*"
        })

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Ask a question about your data..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            with st.spinner("Analyzing database..."):
                try:
                    # prepare history for agent (excluding the last user prompt which is passed directly)
                    # Agent expects list of dicts with role/content
                    history_for_agent = [
                        {"role": m["role"], "content": m["content"]} 
                        for m in st.session_state.messages[:-1]
                        if m["role"] in ["user", "assistant"]
                    ]
                    
                    response = process_chat_query(prompt, history=history_for_agent)
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# For testing directly
if __name__ == "__main__":
    render()
