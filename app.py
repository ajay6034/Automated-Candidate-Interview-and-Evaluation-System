from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.base import TaskResult
from typing import Optional

import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI()

# mount Static files and Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

OPENAI_API_KEY = os.getenv("OPENAI_APIKEY")
model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key=OPENAI_API_KEY)


# --- WebSocket Handler ---
class WebSocketInputHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def get_input(
        self,
        prompt: str,
        cancellation_token: Optional[object] = None
    ) -> str:
        try:
            # Signal frontend that it's user's turn
            await self.websocket.send_text("SYSTEM_TURN:USER")
            data = await self.websocket.receive_text()
            return data
        except WebSocketDisconnect:
            print("Client disconnected during input wait.")
            return "TERMINATE"


async def create_interview_team(websocket: WebSocket, job_position: str):
    handler = WebSocketInputHandler(websocket)

    interviewer_agent = AssistantAgent(
        name="Interviewer",
        model_client=model_client,
        description=f"An AI Agent that conducts interviews for a {job_position} position",
        system_message=f"""You are a professional interviewer for a {job_position} position.
Ask one clear question at a time and wait for the user response.
Ask 5 questions total (technical skills, experience, problem solving).
After completion, say 'TERMINATE' at the end. Each question under 50 words."""
    )

    # Candidate agent (use WebSocket input, not terminal input)
    candidate = UserProxyAgent(
        name="candidate",
        description=f"An agent that represents a candidate for a {job_position} position",
        input_func=handler.get_input
    )

    evaluation_agent = AssistantAgent(
        name="Evaluator",
        model_client=model_client,
        description=f"An AI Agent that provides feedback and advice to candidates for a {job_position} position.",
        system_message=f"""You are a career coach specializing in preparing candidates for {job_position} interviews.
Provide constructive feedback on the candidate's response and suggest improvements.
After the interview, summarize performance and provide actionable advice. Under 100 words."""
    )

    terminate_condition = TextMentionTermination(text="TERMINATE")
    team = RoundRobinGroupChat(
        participants=[interviewer_agent, candidate, evaluation_agent],
        termination_condition=terminate_condition,
        max_turns=20
    )

    return team  # ✅ IMPORTANT


# -- Routes --
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws/interview")
async def websocket_endpoint(websocket: WebSocket, pos: str = Query("Enter the Job Role who are looking")):
    await websocket.accept()

    try:
        team = await create_interview_team(websocket, pos)

        await websocket.send_text(f"SYSTEM_INFO:Starting interview for {pos}...")

        async for message in team.run_stream(task="Start the interview."):
            if isinstance(message, TaskResult):
                await websocket.send_text(f"SYSTEM_END:{message.stop_reason}")
            else:
                await websocket.send_text(f"{message.source}:{message.content}")

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"Error: {e}")
