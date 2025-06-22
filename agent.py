from typing import Literal, List, Any

from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict, Annotated
from langchain_core.prompts.chat import ChatPromptTemplate
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from prompt_library.prompt import system_prompt

from utils.llms import LLMModel
from toolkit.toolkits import *
from toolkit.toolkits import reschedule_appointment, check_availability_by_doctor, check_availability_by_specialization
import os
from utils.Clean_messages import clean_messages, generate_confirmation_context




 #1. Define Pydantic schemas for routing
class Router(BaseModel):
    next: Literal["information_node", "booking_node", "confirmation_node","FINISH"] = Field(
        ..., description="Which specialized worker to call next"
    )
    reasoning: str = Field(..., description="Internal reasoning of the agent")


# 2. Define the state model with defaults
# class AgentState(TypedDict):
#     messages: list[Any]
#     id_number: int
#     next: str = Field("supervisor", description="Next node to call")
#     query: str = Field("", description="Original user query")
#     current_reasoning: str = Field("", description="Model’s internal reasoning")

class AgentState(TypedDict):
    messages: list[Any]
    id_number: int
    next: str = Field("supervisor", description="Next node to call")
    query: str = Field("", description="Original user query")
    current_reasoning: str = Field("", description="Model's internal reasoning")
    interrupted: bool = Field(False, description="Flag for interruption status")

class DoctorAppointmentAgent:
    def __init__(self):
        llm_model = LLMModel()
        self.llm_model=llm_model.get_model()


    def create_confirmation_message(self, reasoning: str, user_query: str) -> str:
        """
        Create a clear confirmation message based on the supervisor's reasoning
        """

        confirmation_message = f"""
        Based on your request: "{user_query}"

        I understand that: {reasoning}

        Before I proceed, I need to confirm the following details with you:

        Please review and confirm if this is correct, or let me know if you'd like to make any changes.

         Would you like me to proceed with this understanding? (Please respond with 'yes' to confirm or provide corrections)
        """.strip()

        return confirmation_message
    

    def create_final_response(self, state: AgentState, reasoning: str) -> str:
        """
        Create a final response message for the user when workflow completes
        """
    # Look for booking confirmation in recent messages
        recent_messages = state.get("messages", [])[-5:]  # Last 5 messages
    
        booking_info = ""
        for msg in reversed(recent_messages):
            if isinstance(msg, AIMessage) and ("booking" in msg.content.lower() or "confirmed" in msg.content.lower()):
                booking_info = msg.content
                break
    
        if booking_info:
            # If we found booking info, return it
            return f"{booking_info}\n\nIs there anything else I can help you with?"
        else:
            # Generic completion message
            return f"Task completed successfully. {reasoning}\n\nIs there anything else I can help you with?"


    
    
    def supervisor_node(self, state: AgentState) -> Command[Literal['information_node', 'booking_node', 'confirmation_node', '__end__']]:

        print("**************************SUPERVISOR ENTRY****************************")
        print(f"Current state: {state}")
        print("="*70)

        # print("sys prompt:: ", system_prompt)
    
    # Clean messages to avoid duplicates
        clean_msgs = clean_messages(state.get("messages", []))
    
    # Build messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"user's identification number is {state['id_number']}"},
        ] + clean_msgs
    
    # Get the current query
        query = ""
        if clean_msgs:
            for msg in reversed(clean_msgs):
                if isinstance(msg, HumanMessage) and "identification number" not in msg.content:
                    query = msg.content
                    break
    
        print(f"Current query: {query}")
    
        try:
            print("llm calling...")
            response = self.llm_model.with_structured_output(Router).invoke(messages)
            goto = response.next
        
            print(f"🤖 LLM Decision: {goto} - Reasoning: {response.reasoning}")


            if goto == "FINISH":
            # Before ending, make sure user gets the final response
                final_message = self.create_final_response(state, response.reasoning)
                updated_messages = clean_msgs + [AIMessage(content=final_message)]
            
                return Command(
                    goto="__end__",  # Use __end__ instead of FINISH
                    update={
                    "next": "FINISH",
                    "query": clean_msgs[-1].content if clean_msgs else "",
                    "current_reasoning": response.reasoning,
                    "messages": updated_messages
                    }
                )
        
        # **IMPROVED**: Add reasoning as AI message when going to confirmation
            updated_messages = clean_msgs
            if goto == "confirmation_node":
            # Create a clear confirmation context message using the reasoning
                confirmation_context = self.create_confirmation_message(response.reasoning, query)
                updated_messages = clean_msgs + [AIMessage(content=confirmation_context)]
                print(f"📋 Added confirmation context: {confirmation_context}")
        
            return Command(
                goto=goto if goto != "FINISH" else "__end__",
                update={
                    "next": goto,
                    "query": clean_msgs[-1].content if clean_msgs else "",
                    "current_reasoning": response.reasoning,
                    "messages": updated_messages  # Use updated messages
                }
            )
        
        except Exception as e:
            print(f"❌ Error in supervisor: {e}")
            return Command(
                goto="information_node",
                update={
                    "next": "information_node",
                    "current_reasoning": "Fallback to information node due to error",
                    "messages": clean_msgs
                }
            )


    def information_node(self, state: AgentState) -> Command[Literal['supervisor']]:


        print("*****************INFORMATION NODE CALLED************")

        system_prompt = """You are an intelligent hospital information agent. Your job is to:

    1. Help users check doctor availability using the tools provided.
    2. Provide clear, concise information about available slots.
    3. If the user asks to book, do NOT book or simulate confirmation. Instead, politely state that a booking agent will handle the reservation.
    4. Do NOT confirm bookings or give booking confirmations — your role is strictly informational.
    5. Be polite, clear, and avoid overstepping your responsibilities.

    Important:
    - The current year is 2024.
    - Always state doctor names and exact available times.
    - If the requested time isn't available, suggest the nearest options.
    - If the user mentions booking or confirms they'd like to book, pass the intent along clearly (e.g., "User would like to proceed with booking") so a supervisor/booking agent can take over.

    You have access to the following tools:
    - check_availability_by_doctor
    - check_availability_by_specialization
    """

        prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ])
         
# Create the agent with your existing tools
        information_agent = create_react_agent(
        model=self.llm_model,
        tools=[check_availability_by_doctor, check_availability_by_specialization],
        prompt=prompt
        )

        try:    

# Clean messages before processing

            cleaned = clean_messages(state["messages"])
            if "id_number" in state:
                cleaned.insert(0, HumanMessage(content=f"My identification number is {state['id_number']}."))

            if "current_reasoning" in state:
                cleaned.insert(1, AIMessage(content=f"Reasoning: {state['current_reasoning']}", name="supervisor_node"))

            
            print("info : ", cleaned)

            # print(information_agent)
            result = information_agent.invoke({"messages": cleaned} )

            print(f"Information agent result: {result['messages'][-1].content}")

            print("next..")

# Add the response to conversation
            new_message = AIMessage(
            content=result['messages'][-1].content, 
            name="information_node"
            )

            updated_messages = cleaned + [new_message]

            

            return Command(
            update={"messages": updated_messages}, 
            goto="supervisor"
            )

        except Exception as e:
            print(f"❌ Error in information_node: {e}")

# Fallback response
            error_message = AIMessage(
            content="I'm having trouble checking availability right now. Please try again or contact support.",
            name="information_node"
    )

            return Command(
            update={"messages": state["messages"] + [error_message]}, 
            goto="supervisor"
            )



    def booking_node(self, state: AgentState) -> Command[Literal['supervisor']]:

        print("*****************BOOKING NODE CALLED************")
    
        system_prompt = """
    You are a specialized booking agent for hospital appointments. Your job is to:

    1. Use the provided tools—set_appointment, cancel_appointment, reschedule_appointment—to perform exactly one of: book, cancel, or reschedule.
    2. If you lack availability context, first call the appropriate availability tool (check_availability_by_doctor or check_availability_by_specialization) and interpret its output.
    3. Extract date and time information correctly in the format DD‑MM‑YYYY HH:MM.
    4. Respect implicit confirmations like “go ahead” or “just book it” from the user; do not pause for extra confirmation in those cases.
    5. Handle any booking errors gracefully.

    Important:
    - Current year is 2024.
    - Always confirm (in your JSON) the doctor, date, and time before finalizing.
    - Never simulate availability checks or confirmations—the agent’s only role is to call tools and report results.

    Output: your **only** response must be a single JSON object (no extra text) with these fields:
    - "status": "success" or "failure"
    - "action": "book", "cancel", or "reschedule"
    - "doctor": the doctor’s full name
    - "date": "DD-MM-YYYY"
    - "time": "HH:MM"
    - "message": a human-readable summary
    - (if status is "failure") include "reason"

    Examples (use double‐curly braces to escape in the template):
    ✅ {{ "status": "success",  "action": "cancel",     "doctor": "Dr. John Doe",   "date": "08-08-2024", "time": "16:30", "message": "Successfully cancelled appointment with Dr. John Doe on 08-08-2024 at 16:30." }}
    ❌ {{ "status": "failure",  "action": "book",      "doctor": "Dr. Jane Smith", "date": "15-09-2024", "time": "10:00", "reason": "No available slots at that time." }}
    """


    
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages")
        ])
    
    # Create agent with your existing booking tools
        booking_agent = create_react_agent(
            model=self.llm_model,
            tools=[set_appointment, cancel_appointment, reschedule_appointment],
            prompt=prompt
    )
    
        try:
        # Clean messages before processing
            cleaned = clean_messages(state["messages"])
            if "id_number" in state:
                cleaned.insert(0, HumanMessage(content=f"My identification number is {state['id_number']}."))

            if "current_reasoning" in state:
                cleaned.insert(1, AIMessage(content=f"Reasoning: {state['current_reasoning']}", name="supervisor_node"))


            result = booking_agent.invoke({"messages": cleaned})

        
            print(f"Booking agent result: {result['messages']}")
        
        # Add the response to conversation
            new_message = AIMessage(
                content=result['messages'][-1].content,
                name="booking_node"
            )
        
            updated_messages = cleaned + [new_message]
        
            return Command(
            update={"messages": updated_messages},
            goto="supervisor"
        )
        
        except Exception as e:
            print(f"❌ Error in booking_node: {e}")
        
        # Fallback response
            error_message = AIMessage(
            content="I'm having trouble processing the booking right now. Please try again or contact support.",
            name="booking_node"
            )
        
            return Command(
            update={"messages": state["messages"] + [error_message]},
            goto="supervisor"
        )


    ### working human in loop

#     def confirmation_node(self, state: AgentState) -> Command[Literal['supervisor']]:
#         """
#         Pause the graph to get a human confirmation via LangGraph interrupt,
#         then resume by injecting the user's response as a HumanMessage.
#         """

#         print("------------inside pf confirmation_node ------------")

#     # Last question prompt
#         last_ai: AIMessage = state['messages'][-1]
#     # # Use interrupt to get human input in production-friendly way
#     # response_text = interrupt(f"{last_ai.content}\nYour response:")

#   # Check if we're in development mode
#         is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
    
#         if is_development:
#         # Use simple input() for development
#             print("\n" + "="*50)
#             print("WAITING FOR YOUR RESPONSE:")
#             print("="*50)
#             print(f"Question: {last_ai.content}")
#             print("="*50)
        
#             try:
#             # Get user input
#                 response_text = input("Your response: ").strip()
            
#                 if not response_text:
#                     response_text = "Please provide a valid response"
                
#                 print(f"You responded: {response_text}")
            
#             except KeyboardInterrupt:
#                 print("\nInput cancelled")
#                 response_text = "I need to cancel this request"
#             except Exception as e:
#                 print(f"Error getting input: {e}")
#                 response_text = "There was an error with my response"
            
#         else:
#         # Use LangGraph interrupt for production
#             try:
#                 from langgraph.types import interrupt
#                 response_text = interrupt(f"{last_ai.content}\n\nYour response:")
#             except Exception as e:
#                 print(f"Interrupt failed: {e}")
#                 response_text = "Interrupt not available in this environment"

#     # Append human response to conversation
#         human_msg = HumanMessage(content=response_text)
#         updated_msgs = state['messages'] + [human_msg]

#         return Command(
#             goto="supervisor",
#             update={"messages": updated_msgs}
#         )

    def confirmation_node(self, state: AgentState) -> Command[Literal['supervisor']]:
        """Human-in-the-loop confirmation using interrupt pattern"""
        
        print("🔔 Entering confirmation node") 

        last_ai_msg = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage):
                last_ai_msg = msg
                break
    
        if last_ai_msg:
        # Use the AI message that contains the reasoning context
            confirmation_prompt = last_ai_msg.content
        else:
        # Fallback - use reasoning from state if available
            reasoning = state.get("confirmation_reasoning", "")
            if reasoning:
                confirmation_prompt = f"""
                    I need to confirm: {reasoning}
                    Please confirm if this is correct by responding 'yes' or provide any corrections needed.
                      """.strip()
            else:
                confirmation_prompt = "Please confirm your request. Respond 'yes' to proceed or provide corrections."
        
        print(f"📋 Confirmation prompt: {confirmation_prompt}")
        
        # THIS IS THE KEY - Use interrupt() function as shown in screenshot
        # This will pause execution and return control to the calling code
        user_response = interrupt(confirmation_prompt)
        
        print(f"✅ User confirmed with: {user_response}")
        
        # This code runs AFTER the user provides confirmation
        # Add the user's response to messages
        updated_messages = state["messages"].copy()
        updated_messages.append(HumanMessage(content=user_response))
        
         
        # When resumed, this will execute with the user's response
        human_msg = HumanMessage(content=user_response)
        
        return Command(
            update={"messages": state["messages"] + [human_msg]},
            goto="supervisor"
        )



    def workflow(self) -> StateGraph:

        # Create checkpointer - THIS IS CRUCIAL
        checkpointer = MemorySaver()

        workflow = StateGraph(AgentState)
        
        # Define nodes (unchanged)
        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("information_node", self.information_node)
        workflow.add_node("booking_node", self.booking_node)
        workflow.add_node("confirmation_node", self.confirmation_node)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Define edges (unchanged)
        workflow.add_conditional_edges(
            "supervisor",
            lambda state: state["next"],
            {
                "information_node": "information_node",
                "booking_node": "booking_node",
                "confirmation_node": "confirmation_node",
                "FINISH": END,  
                "__end__": END  
            }
        )
        
        workflow.add_edge("information_node", "supervisor")
        workflow.add_edge("booking_node", "supervisor")
        workflow.add_edge("confirmation_node", "supervisor")
        
          # COMPILE WITH CHECKPOINTER - This is the key!
        return workflow.compile(checkpointer=checkpointer)