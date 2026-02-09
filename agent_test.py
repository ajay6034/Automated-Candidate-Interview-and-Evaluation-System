from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import RoundRobinGroupChat
from dotenv import load_dotenv
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.base import TaskResult
import os

load_dotenv()

OPEAI_APIKEY = os.getenv("OPENAI_APIKEY")

model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key= OPEAI_APIKEY)

print("Setting up Agents...")

## Creating Interviewer Agent For Interviewing the Candidate

async def my_agent(job_position= "Enter the Job Role who are looking"):
    interviewer_agent = AssistantAgent(
        name = "Interviewer",
        model_client = model_client,
        description =f"An AI Agent that conducts interviews for a {job_position} position",
        system_message=f''' You are a job professional interviewer for a {job_position} position.
        Ask one clear question at a time and wait for the user response. Your job is continue and ask questions, dont pay any attention to career coach response.
        Make sure to ask question based on candidate's and your expertise in the field. Ask 5 questions in total covering technical skills and 
        experience, problem solving abilities. After completion of asking questions, say 'Terminate' at the end odf the interview. Make a question under 50 words '''

    )


## Creating candidate agent i.e User Agent who can give input but it is not Automated

    candidate = UserProxyAgent(
        name = "candidate",
        description = f"An agent that simulates a candidate for a {job_position} position",
        input_func= input
    )

## Creating evalution Agent who evaluates candidate response and who communicates with Interviewer agent


    evaluation_agent = AssistantAgent(
        name = "Evaluator",
        model_client = model_client,
        description =f"An AI Agent that provides feedback and advice to candidates for a {job_position} position.",
        system_message= f'''You are a career coach specializing in preparating candidates for {job_position} interviews.
        provide constructive feedback on the candidates response and suggest improvements. After the interview, summarize the candidates
        performance and provide actionable advice. Make it under 100 words'''
    )

## Integration of the Agents For parallel communication between them.

    terminate_condition = TextMentionTermination(text = "TERMINATE")
    team = RoundRobinGroupChat(
        participants= [interviewer_agent, candidate, evaluation_agent], # agents should be in sequence as created
        termination_condition= terminate_condition,
        max_turns = 20
    )

    return team # object here is team 


## Testing the Agents 

async def run_interview(team):
    async for message in team.run_stream(task =' Start the interview with the first question?'):

        if isinstance(message, TaskResult):
            message = f' Interview completed with result: {message.stop_reason}'
            yield message
        else:
            message = f'{message.source}: {message.content}'
            yield message

async def main():
    job_position = "Enter the Job Role who are looking"
    team = await my_agent(job_position)


    async for message in run_interview(team):
        print('_'*50)
        print(message)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
