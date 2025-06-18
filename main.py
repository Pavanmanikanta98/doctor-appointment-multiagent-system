from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from agent import DoctorAppointmentAgent
from langgraph.types import Command
from langgraph.errors import GraphInterrupt
import os
import traceback

os.environ.pop("SSL_CERT_FILE", None)

app = FastAPI()

# Define Pydantic model to accept request body
class UserQuery(BaseModel):
    id_number: int
    messages: str
    session_id: str = None
    is_confirmation: bool = False

agent = DoctorAppointmentAgent()
app_graph = agent.workflow()

# Session storage (in-memory for simplicity)
sessions = {}

def serialize_messages(messages):
    """Convert messages to serializable format"""
    
    serializable_messages = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            serializable_messages.append({"role": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            serializable_messages.append({"role": "ai", "content": msg.content})
    return serializable_messages



@app.post("/execute")
def execute_agent(user_input: UserQuery):
    print(f"🔵 Received request: confirmation={user_input.is_confirmation}, session_id={user_input.session_id}")
    
    try:
        # Initialize or retrieve session
        if not user_input.session_id or user_input.session_id not in sessions:
            session_id = str(uuid.uuid4())
            print(f"🆕 Creating new session: {session_id}")
            
            state = {
                "messages": [HumanMessage(content=user_input.messages)],
                "id_number": user_input.id_number,
                "next": "",
                "query": user_input.messages,
                "current_reasoning": "",
            }
            sessions[session_id] = state
        else:
            session_id = user_input.session_id
            state = sessions[session_id]
            print(f"🔄 Using existing session: {session_id}")
            
            # For confirmation responses, add as new human message
            if user_input.is_confirmation:
                print("📝 Adding confirmation message to state")
                state["messages"].append(HumanMessage(content=user_input.messages))
            else:
                # For new queries, add to existing conversation
                print("📝 Adding new query to conversation")
                state["messages"].append(HumanMessage(content=user_input.messages))
                state["query"] = user_input.messages

        print(f"📊 Current state has {len(state['messages'])} messages")


        
        # Execute graph with proper interrupt handling
        if user_input.is_confirmation:
            print("🔄 Resuming from confirmation...")
            # Resume from interruption
            response = app_graph.invoke(
                Command(resume=user_input.messages), 
                {"configurable": {"thread_id": session_id}}
            )
        else:
            print("🚀 Starting new execution...")
            # New execution
            response = app_graph.invoke(
                state,
                {"configurable": {"thread_id": session_id}}
            )
        
        print(f"✅ Graph execution completed")

        # Check if graph was interrupted (based on screenshot pattern)
        graph_state = app_graph.get_state({"configurable": {"thread_id": session_id}})
        print(f"📊 Graph state: {graph_state}")

                # Check for interrupts in state.tasks (as shown in screenshot)
        if hasattr(graph_state, 'tasks') and graph_state.tasks:
            if hasattr(graph_state.tasks[0], 'interrupts') and graph_state.tasks[0].interrupts:
                print("🛑 Interrupt detected in graph state")
                
                # Get the interrupt value (confirmation prompt)
                interrupt_value = graph_state.tasks[0].interrupts[0]
                print(f"📋 Interrupt value: {interrupt_value}")
                
                # Update session with current state
                sessions[session_id] = graph_state.values
                
                return {
                    "session_id": session_id,
                    "status": "confirmation_required",
                    "confirmation_prompt": interrupt_value,
                    "messages": serialize_messages(graph_state.values.get("messages", []))
                }
        
        
        # Update session state
        sessions[session_id] = response
        
        # Return successful response
        return {
            "session_id": session_id,
            "messages": serialize_messages(response["messages"]),
            "status": "success"
        }


    except Exception as e:

        print("❌ Unexpected error occurred:")
        print(traceback.format_exc())
        
        # For debugging - let's see what kind of error this is
        print(f"Exception type: {type(e)}")
        print(f"Exception message: {str(e)}")
        
        # If it's any interrupt-related error, handle gracefully
        error_str = str(e).lower()
        if "interrupt" in error_str:
            print("🤔 Interrupt-related error - checking graph state")
            
            try:
                # Try to get current graph state
                thread_config = {"configurable": {"thread_id": session_id}}
                graph_state = app_graph.get_state(thread_config)
                
                if hasattr(graph_state, 'tasks') and graph_state.tasks:
                    if hasattr(graph_state.tasks[0], 'interrupts') and graph_state.tasks[0].interrupts:
                        interrupt_value = graph_state.tasks[0].interrupts[0]
                        
                        return {
                            "session_id": session_id,
                            "status": "confirmation_required",
                            "confirmation_prompt": interrupt_value,
                            "messages": serialize_messages(graph_state.values.get("messages", []))
                        }
            except Exception as state_error:
                print(f"Error getting graph state: {state_error}")
        
        # Handle other errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")  
        
    # except Exception as e:
    #     print("❌ Unexpected error occurred:")
    #     print(traceback.format_exc())
        
    #     # Check if this might be an interrupt that wasn't caught properly
    #     error_str = str(e).lower()
    #     if "interrupt" in error_str or "confirmation" in error_str:
    #         print("🤔 Looks like an interrupt - handling as confirmation")
            
    #         # Update session with current state
    #         sessions[session_id] = state
            
    #         # Find last AI message for confirmation prompt
    #         last_ai_content = "Please confirm the appointment details"
    #         for msg in reversed(state["messages"]):
    #             if isinstance(msg, AIMessage):
    #                 last_ai_content = msg.content
    #                 break
                    
    #         return {
    #             "session_id": session_id,
    #             "status": "confirmation_required", 
    #             "confirmation_prompt": last_ai_content,
    #             "messages": serialize_messages(state["messages"])
    #         }
        
    #     # Handle other errors
    #     raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Debug endpoint to inspect session state"""
    if session_id in sessions:
        state = sessions[session_id]
        return {
            "session_id": session_id,
            "messages": serialize_messages(state["messages"]),
            "message_count": len(state["messages"]),
            "query": state.get("query", ""),
            "next": state.get("next", ""),
            "reasoning": state.get("current_reasoning", "")
        }
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/sessions")
def list_sessions():
    """Debug endpoint to list all sessions"""
    return {
        "sessions": list(sessions.keys()),
        "count": len(sessions)
    }



@app.get("/debug/graph/{session_id}")
def debug_graph_state(session_id: str):
    """Debug endpoint to inspect graph state"""
    try:
        thread_config = {"configurable": {"thread_id": session_id}}
        graph_state = app_graph.get_state(thread_config)
        
        return {
            "session_id": session_id,
            "graph_state": str(graph_state),
            "has_tasks": hasattr(graph_state, 'tasks'),
            "tasks_count": len(graph_state.tasks) if hasattr(graph_state, 'tasks') else 0,
            "has_interrupts": (
                hasattr(graph_state, 'tasks') and 
                graph_state.tasks and 
                hasattr(graph_state.tasks[0], 'interrupts') and 
                graph_state.tasks[0].interrupts
            ) if hasattr(graph_state, 'tasks') and graph_state.tasks else False
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}