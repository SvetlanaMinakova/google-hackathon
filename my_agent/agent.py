from google.adk.agents.llm_agent import Agent


# Mock tool implementation
def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city."""
    return {"status": "success", "city": city, "time": "10:30 AM"}


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Creates a fictional Halloween character.",
    instruction="You are a helpful assistant that helps a user to "
                "creates a fictional Halloween character. When user "
                "asks for a character, create both an interesting "
                "background and a vivid description of the character "
                "appearance suitable for image generation."
)
