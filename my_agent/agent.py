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
                "create a fictional Halloween character.\n"
                "Guide the user to choose some details for their character"
                "like gender, age, country of origin etc."
                "When user have provided sufficient details,"
                "use the details to create both a compelling "
                "background and a vivid description of the character "
                "appearance suitable for image generation."
)
