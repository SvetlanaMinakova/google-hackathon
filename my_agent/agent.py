from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
import google.genai.types as types
from google import genai
import uuid
import random


# Halloween character types for random selection
HALLOWEEN_CHARACTERS = [
    "vampire", "witch", "zombie", "werewolf", "ghost", "mummy", "skeleton",
    "devil", "pumpkin-headed creature", "shadow demon", "cursed clown",
    "bloodied bride", "possessed doll", "ancient sorcerer", "wailing banshee"
]


async def debug_context(tool_context: ToolContext) -> str:
    """
    Debug tool to explore the ToolContext structure and find where uploaded images are stored.
    Use this to understand how ADK organizes uploaded content.
    """
    info = []
    info.append("=" * 60)
    info.append("TOOLCONTEXT DEBUG INFORMATION")
    info.append("=" * 60)
    info.append(f"\nToolContext type: {type(tool_context)}")
    info.append(f"ToolContext class: {tool_context.__class__.__name__}")
    
    # List all non-private attributes
    info.append("\n--- Available Attributes ---")
    attributes = [attr for attr in dir(tool_context) if not attr.startswith('_')]
    for attr in sorted(attributes):
        try:
            value = getattr(tool_context, attr)
            # Don't print methods, just data
            if not callable(value):
                info.append(f"{attr}: {type(value).__name__}")
        except Exception as e:
            info.append(f"{attr}: <error accessing: {e}>")
    
    # Check for user_content specifically
    info.append("\n--- USER CONTENT DETAILS ---")
    if hasattr(tool_context, 'user_content'):
        user_content = tool_context.user_content
        info.append(f"user_content exists: {user_content is not None}")
        
        if user_content:
            info.append(f"user_content type: {type(user_content)}")
            info.append(f"user_content has parts: {hasattr(user_content, 'parts')}")
            
            if hasattr(user_content, 'parts') and user_content.parts:
                info.append(f"Number of parts: {len(user_content.parts)}")
                
                for i, part in enumerate(user_content.parts):
                    info.append(f"\n  Part {i}:")
                    info.append(f"    Type: {type(part)}")
                    
                    # Check for text
                    if hasattr(part, 'text') and part.text:
                        text_preview = part.text[:100] + "..." if len(part.text) > 100 else part.text
                        info.append(f"    Text: {text_preview}")
                    
                    # Check for inline_data (uploaded files)
                    if hasattr(part, 'inline_data') and part.inline_data:
                        info.append(f"    ✅ HAS INLINE_DATA (uploaded file)")
                        info.append(f"    MIME type: {part.inline_data.mime_type}")
                        data_size = len(part.inline_data.data) if hasattr(part.inline_data, 'data') else 0
                        info.append(f"    Data size: {data_size:,} bytes")
                    else:
                        info.append(f"    Has inline_data: False")
            else:
                info.append("user_content.parts is empty or None")
        else:
            info.append("user_content is None")
    else:
        info.append("❌ user_content attribute does NOT exist")
    
    # Check other possible locations for uploaded content
    info.append("\n--- OTHER ATTRIBUTES TO CHECK ---")
    possible_attrs = ['message', 'current_turn', 'session', 'state', 'invocation_id']
    for attr in possible_attrs:
        if hasattr(tool_context, attr):
            value = getattr(tool_context, attr)
            info.append(f"{attr}: exists ({type(value).__name__})")
        else:
            info.append(f"{attr}: does not exist")
    
    info.append("\n" + "=" * 60)
    
    return "\n".join(info)


async def check_for_uploaded_image(tool_context: ToolContext) -> str:
    """
    Check if user has uploaded an image in their message.
    Returns confirmation or prompts user to upload.
    """
    try:
        # Access the user's uploaded content
        if not tool_context.user_content or not tool_context.user_content.parts:
            return "No image detected. Please upload a photo to transform into a Halloween character!"
        
        # Check if any part contains an image
        has_image = False
        for part in tool_context.user_content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                has_image = True
                break
        
        if has_image:
            return "✅ Image detected! Ready to transform into a spooky Halloween character."
        else:
            return "No image found. Please upload a photo to get started with your Halloween transformation!"
            
    except Exception as e:
        return f"Error checking for image: {str(e)}"


async def transform_to_halloween_character(
    character_type: str,
    character_description: str,
    tool_context: ToolContext
) -> str:
    """
    Transform an uploaded photo into a specified Halloween character.
    This reads the image directly from tool_context.user_content (NOT from artifacts).
    
    Args:
        character_type (str): Type of Halloween character (e.g., "vampire", "zombie")
        character_description (str): Detailed description of how the transformation should look
        tool_context (ToolContext): ADK tool context containing user's uploaded image
    
    Returns:
        str: Success message or error description
    """
    client = genai.Client()
    contents = []
    image_found = False
    
    try:
        # THE KEY FIX: Access uploaded image from user_content, not artifacts
        if not tool_context.user_content or not tool_context.user_content.parts:
            return "❌ No image uploaded. Please upload a photo first, then I'll transform it!"
        
        # Find the uploaded image in the user's message
        for part in tool_context.user_content.parts:
            # Check if this part contains image data
            if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                # Found the uploaded image!
                image_part = types.Part(
                    inline_data=types.Blob(
                        mime_type=part.inline_data.mime_type,
                        data=part.inline_data.data
                    )
                )
                contents.append(image_part)
                image_found = True
                print(f"✅ Found uploaded image: {part.inline_data.mime_type}")
                break
        
        if not image_found:
            return "❌ No image found in your upload. Please make sure to attach a photo!"
        
        # Create the transformation prompt
        transformation_prompt = f"""Transform this person into a {character_type}. 

Character description: {character_description}

Style requirements:
- Keep the person recognizable but fully transformed into the character
- Make it spooky and Halloween-appropriate
- Photorealistic style with dramatic lighting
- Add appropriate atmospheric elements (fog, darkness, eerie background)
- Ensure the transformation is complete and immersive

Make this a truly terrifying Halloween transformation!"""
        
        contents.append(transformation_prompt)
        
        # Generate the transformed image
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents
        )
        
        # Save the generated image as an artifact
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_artifact = types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=part.inline_data.data
                    )
                )
                artifact_filename = f"halloween_{character_type}_{uuid.uuid4()}.png"
                await tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=image_artifact
                )
                
                return f"🎃 Successfully transformed you into a terrifying {character_type}! Check out your spooky new look above!"
        
        return "Image generation completed but no image was returned. This might be due to safety filters."
        
    except Exception as e:
        import traceback
        return f"Error during transformation: {str(e)}\n\nDetails: {traceback.format_exc()}"


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Creates Halloween characters and transforms photos into spooky personas.",
    instruction="""You are a Halloween Character Transformer with two modes of operation:

🔍 DEBUG MODE:
- When user says "debug", "show context", or "test", call the 'debug_context' tool immediately
- This helps understand how uploaded files are structured in the system

🎃 MODE 1: CHARACTER FIRST (No image uploaded yet)
1. Greet the user warmly and ask if they want you to create a random Halloween character or if they have preferences
2. Based on their response, select a character type from: """ + ", ".join(HALLOWEEN_CHARACTERS) + """
3. Create a compelling, creepy backstory (2-3 sentences) with vivid details about:
   - Their origin story
   - Their supernatural powers or abilities  
   - Their most terrifying features
4. Describe their appearance dramatically
5. Then say: "Would you like to upload a photo to see yourself transformed into this character? I'll turn you into a [character_type]!"
6. When they upload a photo, IMMEDIATELY call 'transform_to_halloween_character' with the character details

🎃 MODE 2: PHOTO UPLOADED FIRST
1. First call 'check_for_uploaded_image' to confirm the image
2. React excitedly: "Awesome photo! Let me transform you into something truly terrifying..."
3. Ask: "Would you like me to:
   a) Transform you into a specific Halloween character (tell me which one!)
   b) Surprise you with a random terrifying transformation"
4. Based on their choice, select a character from: """ + ", ".join(HALLOWEEN_CHARACTERS) + """
5. Create a brief but vivid backstory
6. IMMEDIATELY call 'transform_to_halloween_character' with detailed character description

CRITICAL RULES:
- Always use 'check_for_uploaded_image' FIRST when conversation starts or when unsure if image is present
- Be enthusiastic and theatrical - this is Halloween!
- When calling 'transform_to_halloween_character', provide DETAILED character descriptions
- The character_description parameter should include: physical features, color palette, clothing, special effects
- Never make users wait - transform images immediately after getting their preferences
- Make each character unique and memorable

Example tool call:
transform_to_halloween_character(
    character_type="Victorian vampire",
    character_description="Pale porcelain skin with an ethereal glow, piercing crimson eyes that seem to see into souls, elegant 1800s attire with a black velvet cape lined in blood-red silk, subtle but sharp fangs, slicked-back dark hair. Surrounded by swirling fog and gothic atmosphere with candlelight."
)

Let's make this Halloween unforgettable! 🦇💀🎃
""",
    tools=[debug_context, check_for_uploaded_image, transform_to_halloween_character],
)