from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
import google.genai.types as types
from google import genai
import uuid


async def generate_image(prompt: str, tool_context: ToolContext) -> str:
    """
    Generate an image using Nano Banana (Gemini 2.5 Flash Image) model via Google GenAI SDK.

    Args:
        prompt (str): Descriptive prompt for image generation.

    Returns:
        str: Path to the saved image file.
    """
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash-image", contents=[prompt]
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_artifact = types.Part(
                inline_data=types.Blob(
                    mime_type="image/png", data=part.inline_data.data
                )
            )
            await tool_context.save_artifact(filename=str(uuid.uuid4()), artifact=image_artifact)


            return "Successfully generated and saved the character image"
    return "No image generated"


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Creates a fictional Halloween character.",
    instruction="You are a helpful assistant that helps a user to "
    "create a fictional Halloween character.\n"
    "When user have provided sufficient details or requested"
    "the character generation, use the details to create both a compelling "
    "background and vivid description of character appearance.\n"
    "When the description is generated use 'generate_image' tool "
    "to generate the image of the character",
    tools=[generate_image],
)
