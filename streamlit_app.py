import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8003/execute" 

st.title("🩺 Doctor Appointment System")

def process_api_response(response):
    """Process API response and update session state"""
    st.write('🔄 Processing API response...')
    st.write("🔴 Raw API response:", response)
    
    # Always update session ID if present
    if "session_id" in response:
        st.session_state.session_id = response["session_id"]
    
    # Handle confirmation requirement
    if response.get("status") == "confirmation_required":
        st.session_state.confirmation_active = True
        st.session_state.confirmation_prompt = response.get("confirmation_prompt", "Please confirm:")
        st.write("✅ Confirmation state activated")
        
        # Add confirmation prompt to conversation if not already present
        confirmation_msg = {
            "role": "ai",
            "content": st.session_state.confirmation_prompt
        }
        if confirmation_msg not in st.session_state.conversation:
            st.session_state.conversation.append(confirmation_msg)
    else:
        # Normal response processing
        st.session_state.confirmation_active = False
        st.session_state.confirmation_prompt = ""
        
        # Add new messages to conversation history
        new_messages = response.get("messages", [])
        for msg in new_messages:
            # Avoid duplicates
            if msg not in st.session_state.conversation:
                st.session_state.conversation.append(msg)
    
    st.write("✅ API response processed successfully")

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'confirmation_active' not in st.session_state:
    st.session_state.confirmation_active = False
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'confirmation_prompt' not in st.session_state:
    st.session_state.confirmation_prompt = ""
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""

# Debug information
st.sidebar.markdown("### Debug State")
st.sidebar.write("Session ID:", st.session_state.session_id)
st.sidebar.write("Confirmation Active:", st.session_state.confirmation_active)
st.sidebar.write("User ID:", st.session_state.user_id)
st.sidebar.write("Conversation Length:", len(st.session_state.conversation))

# Display conversation history
st.subheader("📋 Conversation History")
for i, msg in enumerate(st.session_state.conversation):
    if msg["role"] == "human":
        st.markdown(f"**You**: {msg['content']}")
    else:
        st.markdown(f"**Assistant**: {msg['content']}")

# Main debug info
st.write("🔍 Current confirmation_active state:", st.session_state.confirmation_active)

# Confirmation input (only shown when needed)
if st.session_state.confirmation_active:
    st.subheader("⚠️ Confirmation Required")
    st.info(st.session_state.confirmation_prompt)
    
    # Use a form for confirmation
    with st.form("confirmation_form", clear_on_submit=True):
        confirmation = st.text_input("Your response:", key="confirmation_input")
        submitted = st.form_submit_button("✅ Submit Confirmation")
        
        if submitted and confirmation:
            # Add user's confirmation to conversation
            st.session_state.conversation.append({
                "role": "human", 
                "content": confirmation
            })
            
            payload = {
                "id_number": st.session_state.user_id,
                "messages": confirmation,
                "session_id": st.session_state.session_id,
                "is_confirmation": True
            }
            
            try:
                with st.spinner("Sending confirmation..."):
                    response = requests.post(API_URL, json=payload, verify=False)
                    response.raise_for_status()  # Raise an exception for bad status codes
                    response_json = response.json()
                    
                    st.write("🔵 Confirmation response received:", response_json)
                    process_api_response(response_json)
                    
                    # Clear confirmation state after successful processing
                    st.session_state.confirmation_active = False
                    st.session_state.confirmation_prompt = ""
                    st.rerun()
                    
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Request failed: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error processing confirmation: {str(e)}")
                
        elif submitted and not confirmation:
            st.warning("⚠️ Please enter your confirmation")

# Main input form - only show when not in confirmation mode
if not st.session_state.confirmation_active:
    st.subheader("💬 New Query")
    
    with st.form("main_input", clear_on_submit=False):
        user_id = st.text_input("Enter your ID number:", value=st.session_state.user_id)
        user_query = st.text_area("Enter your query:", value=st.session_state.last_query)
        submitted = st.form_submit_button("🚀 Submit Query")
        
        if submitted:
            if not user_id:
                st.warning("⚠️ Please enter your ID number")
                st.stop()
            
            try:
                st.session_state.user_id = int(user_id)
                st.session_state.last_query = user_query
                
                # Add user query to conversation
                st.session_state.conversation.append({
                    "role": "human",
                    "content": user_query
                })
                
                payload = {
                    "id_number": st.session_state.user_id,
                    "messages": user_query
                }
                
                # Include session_id if available
                if st.session_state.session_id:
                    payload["session_id"] = st.session_state.session_id
                
                with st.spinner("Processing your request..."):
                    response = requests.post(API_URL, json=payload, verify=False)
                    response.raise_for_status()
                    response_json = response.json()
                    
                    st.write("🔵 Main query response received:", response_json)
                    process_api_response(response_json)
                    st.rerun()
                    
            except ValueError:
                st.error("❌ Invalid ID number. Please enter a valid integer.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Request failed: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error processing query: {str(e)}")

# Clear conversation button
if st.sidebar.button("🗑️ Clear Conversation"):
    st.session_state.conversation = []
    st.session_state.session_id = None
    st.session_state.confirmation_active = False
    st.session_state.confirmation_prompt = ""
    st.rerun()

# Show raw session state for debugging
if st.sidebar.checkbox("Show Raw Session State"):
    st.sidebar.json(dict(st.session_state))