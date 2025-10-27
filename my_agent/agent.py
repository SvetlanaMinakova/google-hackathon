from google.adk.agents.llm_agent import Agent
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO


def generate_image(prompt: str):
    """
    Generate an image using Nano Banana (Gemini 2.5 Flash Image) model via Google GenAI SDK.

    Args:
        prompt (str): Descriptive prompt for image generation.

    Returns:
        str: Path to the saved image file.
    """
    filename = "nano_banana_image.png"
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt]
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save(filename)
            return filename
    return None


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
    tools=[generate_image]
)
