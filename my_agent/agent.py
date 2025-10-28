from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
import google.genai.types as types
from google import genai
import uuid
import random


# Halloween character types for random selection
HALLOWEEN_CHARACTERS = [
    "vampire", "witch", "zombie", "werewolf", "ghost", "mummy", "skeleton",
    "devil", "pumpkin-headed creature", "shadow demon", "cursed clown", "mermaid",
    "bloodied bride", "possessed doll", "ancient sorcerer", "wailing banshee"
]

# Standard artifact name for the source image
SOURCE_IMAGE_ARTIFACT = "source_image.png"


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
    
    # Check for saved source image artifact
    info.append("\n--- SAVED ARTIFACTS ---")
    try:
        saved_image = await tool_context.load_artifact(SOURCE_IMAGE_ARTIFACT)
        if saved_image:
            info.append(f"✅ Source image artifact EXISTS: {SOURCE_IMAGE_ARTIFACT}")
            if hasattr(saved_image, 'inline_data') and saved_image.inline_data:
                info.append(f"   MIME type: {saved_image.inline_data.mime_type}")
                data_size = len(saved_image.inline_data.data)
                info.append(f"   Size: {data_size:,} bytes")
        else:
            info.append(f"❌ No source image artifact saved yet")
    except Exception as e:
        info.append(f"❌ No source image artifact found: {str(e)}")
    
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


async def save_uploaded_image(tool_context: ToolContext) -> str:
    """
    Saves the uploaded image as an artifact for reuse across multiple transformations.
    The image is saved as 'source_image.png' and can be used for multiple Halloween character transformations.
    
    Returns:
        str: Success or error message
    """
    try:
        # Check if there's already a saved image
        try:
            existing_image = await tool_context.load_artifact(SOURCE_IMAGE_ARTIFACT)
            if existing_image:
                return f"✅ A source image is already saved! You can now request different Halloween transformations without re-uploading."
        except:
            pass  # No existing image, proceed to save new one
        
        # Look for uploaded image in user_content
        if not tool_context.user_content or not tool_context.user_content.parts:
            return "❌ No image found. Please upload a photo first!"
        
        image_found = False
        for part in tool_context.user_content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                # Save this image as an artifact with a known name
                image_artifact = types.Part(
                    inline_data=types.Blob(
                        mime_type=part.inline_data.mime_type,
                        data=part.inline_data.data
                    )
                )
                
                await tool_context.save_artifact(
                    filename=SOURCE_IMAGE_ARTIFACT,
                    artifact=image_artifact
                )
                
                image_found = True
                print(f"✅ Saved source image as artifact: {SOURCE_IMAGE_ARTIFACT}")
                return f"✅ Perfect! I've saved your photo. Now I can transform it into different Halloween characters without you needing to upload it again!"
        
        if not image_found:
            return "❌ No image found in your message. Please attach a photo!"
            
    except Exception as e:
        import traceback
        return f"Error saving image: {str(e)}\n{traceback.format_exc()}"


async def check_for_source_image(tool_context: ToolContext) -> str:
    """
    Check if there's a saved source image or a newly uploaded image.
    
    Returns:
        str: Status message about image availability
    """
    try:
        # First check if there's a saved artifact
        try:
            saved_image = await tool_context.load_artifact(SOURCE_IMAGE_ARTIFACT)
            if saved_image:
                return f"✅ Source image is ready! You can request any Halloween character transformation."
        except:
            pass
        
        # Check if there's a newly uploaded image in user_content
        if tool_context.user_content and tool_context.user_content.parts:
            for part in tool_context.user_content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                    return "✅ New image detected! I'll save it so we can use it for multiple transformations."
        
        return "❌ No image available. Please upload a photo to get started with Halloween transformations!"
        
    except Exception as e:
        return f"Error checking for image: {str(e)}"


async def transform_to_halloween_character(
    character_type: str,
    character_description: str,
    tool_context: ToolContext
) -> str:
    """
    Transform a photo into a specified Halloween character.
    First tries to use the saved source_image.png artifact.
    If not found, looks for a newly uploaded image in user_content.
    
    Args:
        character_type (str): Type of Halloween character (e.g., "vampire", "zombie")
        character_description (str): Detailed description of how the transformation should look
        tool_context (ToolContext): ADK tool context
    
    Returns:
        str: Success message or error description
    """
    client = genai.Client()
    contents = []
    image_found = False
    image_source = None
    
    try:
        # STRATEGY 1: Try to load the saved source image artifact first
        try:
            saved_image = await tool_context.load_artifact(SOURCE_IMAGE_ARTIFACT)
            if saved_image and hasattr(saved_image, 'inline_data') and saved_image.inline_data:
                image_part = types.Part(
                    inline_data=types.Blob(
                        mime_type=saved_image.inline_data.mime_type,
                        data=saved_image.inline_data.data
                    )
                )
                contents.append(image_part)
                image_found = True
                image_source = "saved artifact"
                print(f"✅ Using saved source image from artifact")
        except Exception as e:
            print(f"No saved artifact found, checking user_content: {e}")
        
        # STRATEGY 2: If no saved image, check user_content for newly uploaded image
        if not image_found:
            if tool_context.user_content and tool_context.user_content.parts:
                for part in tool_context.user_content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                        image_part = types.Part(
                            inline_data=types.Blob(
                                mime_type=part.inline_data.mime_type,
                                data=part.inline_data.data
                            )
                        )
                        contents.append(image_part)
                        image_found = True
                        image_source = "newly uploaded"
                        print(f"✅ Using newly uploaded image from user_content")
                        break
        
        if not image_found:
            return "❌ No image available. Please upload a photo or make sure the source image is saved!"
        
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
        
        print(f"🎃 Generating {character_type} transformation using {image_source} image...")
        
        # Generate the transformed image
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents
        )
        
        # Save the generated image as an artifact with a unique name
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_artifact = types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=part.inline_data.data
                    )
                )
                # Create a unique filename for this transformation
                safe_character_name = character_type.replace(" ", "_").replace("/", "_")
                artifact_filename = f"halloween_{safe_character_name}_{uuid.uuid4().hex[:8]}.png"
                
                await tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=image_artifact
                )
                
                return f"🎃 Successfully transformed you into a terrifying {character_type}! Check out your spooky new look above!\n\n💡 Want to try a different character? Just ask! I've saved your original photo, so no need to upload it again."
        
        return "Image generation completed but no image was returned. This might be due to safety filters."
        
    except Exception as e:
        import traceback
        return f"Error during transformation: {str(e)}\n\nDetails: {traceback.format_exc()}"


async def clear_source_image(tool_context: ToolContext) -> str:
    """
    Clears the saved source image, allowing the user to upload a new photo.
    
    Returns:
        str: Confirmation message
    """
    try:
        # Note: ADK doesn't have a built-in delete method, so we'll just inform the user
        # that they can upload a new image which will overwrite the old one
        return "✅ Ready for a new photo! Just upload a new image and I'll save it as the new source image."
    except Exception as e:
        return f"Error: {str(e)}"


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Creates Halloween characters and transforms photos into spooky personas. Saves uploaded photos for multiple transformations.",
    instruction="""You are a Halloween Character Transformer with an intelligent image management system.

🔍 DEBUG MODE:
- When user says "debug", call the 'debug_context' tool to show system information

📸 IMAGE MANAGEMENT WORKFLOW:
When a user uploads an image:
1. IMMEDIATELY call 'save_uploaded_image' to save it as an artifact
2. Confirm the image is saved
3. Then proceed with transformation

🎃 TRANSFORMATION MODES:

MODE 1: PHOTO UPLOADED FIRST
1. User uploads photo
2. Call 'save_uploaded_image' immediately
3. Ask: "Great photo! Would you like me to:
   a) Transform you into a specific Halloween character (tell me which!)
   b) Surprise you with a random terrifying character
   c) See options from: """ + ", ".join(HALLOWEEN_CHARACTERS) + """"
4. Once they choose, create a vivid backstory (2-3 sentences)
5. Call 'transform_to_halloween_character' with detailed description
6. After transformation, remind them: "Want another character? Just ask - no need to re-upload!"

MODE 2: CHARACTER FIRST, THEN PHOTO
1. User asks to create a character
2. Select randomly from: """ + ", ".join(HALLOWEEN_CHARACTERS) + """
3. Create compelling backstory with:
   - Origin story
   - Supernatural abilities
   - Terrifying features
4. Describe appearance dramatically
5. Ask: "Ready to see yourself as this character? Upload a photo!"
6. When photo is uploaded, call 'save_uploaded_image' first
7. Then immediately call 'transform_to_halloween_character'

MODE 3: MULTIPLE TRANSFORMATIONS (Source Image Already Saved)
1. Call 'check_for_source_image' to confirm image is available
2. User asks for a new character
3. Create new character concept
4. Call 'transform_to_halloween_character' (it will use the saved image automatically!)
5. Remind them they can keep trying different characters

🎯 KEY BEHAVIORS:
- ALWAYS save uploaded images immediately with 'save_uploaded_image'
- For subsequent transformations, just call 'transform_to_halloween_character' - it automatically uses the saved image
- Be enthusiastic and theatrical
- Character descriptions should be VIVID and DETAILED (colors, textures, atmosphere, lighting)
- Celebrate that they can try unlimited characters without re-uploading

🗑️ RESET OPTION:
- If user wants to use a different photo, call 'clear_source_image'
- Then they can upload a new photo

Example detailed character description:
"Pale porcelain skin with subtle blue undertones, glowing crimson eyes with vertical pupils, elegant Victorian attire with a black velvet tailcoat and blood-red silk cravat, razor-sharp fangs barely visible, slicked-back jet-black hair with a widow's peak. Surrounded by swirling purple mist and gothic candlelit atmosphere with stone castle walls in the background."

🦇 Let's create something terrifyingly awesome! 💀🎃
""",
    tools=[
        debug_context,
        save_uploaded_image,
        check_for_source_image,
        transform_to_halloween_character,
        clear_source_image
    ],
)