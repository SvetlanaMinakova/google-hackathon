import asyncio
import logging
import warnings

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types  # For creating message Content/Parts

from my_agent.agent import root_agent

# Ignore all warnings
warnings.filterwarnings("ignore")


logging.basicConfig(level=logging.ERROR)

print("Libraries imported.")


session_service = InMemorySessionService()

APP_NAME = "weather_tutorial_app"


async def create_runner() -> Runner:
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    print(f"Runner created for agent '{runner.agent.name}'.")
    return runner


async def call_agent_async(query: str, runner, user_id, session_id):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>> User Query: {query}")

    if not await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id):
        await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        print(f"Session created: App='{APP_NAME}', User='{user_id}', Session='{session_id}'")
    else:
        print(f"Using existing session: App='{APP_NAME}', User='{user_id}', Session='{session_id}'")

    content = types.Content(role="user", parts=[types.Part(text=query)])
    final_response_text = "Agent did not produce a final response."

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break

    print(f"<<< Agent Response: {final_response_text}")


async def run_conversation():
    USER_ID = "user_1"
    SESSION_ID = "session_001"

    runner = await create_runner()
    await call_agent_async("What is time in Rotterdam?", runner=runner, user_id=USER_ID, session_id=SESSION_ID)

    await call_agent_async("How about Paris?", runner=runner, user_id=USER_ID, session_id=SESSION_ID)

    await call_agent_async("Tell me about it in New York", runner=runner, user_id=USER_ID, session_id=SESSION_ID)


if __name__ == "__main__":
    load_dotenv()
    try:
        asyncio.run(run_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")
