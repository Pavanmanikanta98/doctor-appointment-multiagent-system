# 🏥 Doctor Appointment Multi-Agent System

A modular AI scheduling assistant built using **LangGraph**, **LangChain**, and the **Groq API**. This system coordinates autonomous agents to manage doctor appointments with *human-in-the-loop fallback*, combining flexibility, real-time inference, and a robust, modular design.

![Doctor Appointment Multi-Agent System Demo](https://storage.googleapis.com/gemini-prod/images/e6f15777-b9c1-4b17-a006-2580a82e9efd.jpeg)
*A demonstration of the multi-agent orchestration interface.*

---

## ✨ About The Project

This project is a deep dive into real-world AI orchestration. I built a conversational AI system where multiple agents collaborate to handle appointment scheduling, rescheduling, and availability lookups, achieving end-to-end automation with tool-based reasoning.

The goal was to create a system that is not only intelligent but also resilient. By integrating human-in-the-loop logic, the system gracefully handles ambiguity and unclear user inputs, ensuring a robust and user-aligned experience. The architecture achieves approximately **95% workflow automation**, with intelligent fallback triggers for edge-case handoffs to a human operator.

> ### 🧠 Key Learnings
> * Building real-world AI requires more than just LLMs—agentic workflows, fallbacks, and context management are game-changers.
> * Ambiguity isn’t failure—humans in the loop make the system more robust and user-aligned.
> * GenAI systems shine when combined with smart engineering and intentional design.

---

## 🔧 Tech Stack

-   **Orchestration & State Management:** [LangGraph](https://github.com/langchain-ai/langgraph) & [LangChain](https://github.com/langchain-ai/langchain)
-   **LLM Inference:** Groq API for ultra-fast, low-latency responses
-   **Core Logic & Backend:** Python & FastAPI
-   **Frontend Demo:** Streamlit
-   **Deployment:** Docker

---

## 🧠 Architecture Overview

The system uses a **4-agent LangGraph workflow**. Each agent is a specialist, and the Supervisor routes tasks between them, creating a resilient and logical pipeline.

| Agent                  | Description                                                              |
| ---------------------- | ------------------------------------------------------------------------ |
| 🧾 **Information Agent** | Gathers patient intent, symptoms, preferred time, and department.        |
| 🗓️ **Booking Agent** | Searches for slot availability and handles the booking logic using tools.|
| ✅ **Confirmation Agent**| Verifies outcomes, detects edge cases, and triggers human-in-the-loop.   |
| 🧑‍🏫 **Supervisor Agent** | Controls agent routing, handles fallback logic, and logs workflow status.|

---

## 🧩 Key Features

-   🔁 **Tool-Based Multi-Agent Orchestration** using LangGraph for stateful routing.
-   🧠 **Context-Aware Workflows** with LangChain for memory and tool handling.
-   ⚡ **Low-Latency Inference** powered by the Groq API for real-time conversation.
-   ✅ **95% Workflow Automation** with seamless human-in-the-loop fallback support.
-   🎛️ **Interactive Streamlit Interface** for live demonstration and simulation.
-   📈 **Modular & Extensible Structure** designed to easily accommodate new agents or tasks.

---

## 🚀 Getting Started

Follow these steps to get a local copy up and running.

### Prerequisites

You will need the following installed:
* Python 3.10+
* Git

### 1. Clone the Repository

```bash
git clone [https://github.com/yourusername/doctor-multiagent-system.git](https://github.com/yourusername/doctor-multiagent-system.git)
cd doctor-multiagent-system
```
### 2. Install Dependencies

Create a .env file in the project's root directory and add your Groq API key:

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables

````TOML
GROQ_API_KEY=your_groq_api_key_here
````

### 4. Run the Application

First, start the FastAPI backend server:
```bash
uvicorn backend.main:app --reload --port 8000
```

In a new terminal, run the Streamlit frontend:

```bash
streamlit run ./streamlit_ui.py
```
Open your browser and navigate to http://localhost:8501 to interact with the system.

### 🔮 Roadmap
[x] Multi-agent orchestration using LangGraph

[x] Human-in-the-loop fallback logic

[x] FastAPI backend for REST API interaction

[x] Groq LLM integration for fast inference

[ ] Google Calendar integration for real-time booking

[ ] Implement an async task queue (e.g., Celery or Redis) for scalability

[ ] Add session-based user persistence for multi-turn conversations

### 👨‍💻 Author
Vasamsetti Pavan Manikanta
- Email: pavanmanikanta45@gmail.com
- Portfolio: https://portfolio98-pi.vercel.app/

### 📄 License
This project is licensed under the MIT License. Feel free to fork, use, and build upon it! See the LICENSE file for details.


