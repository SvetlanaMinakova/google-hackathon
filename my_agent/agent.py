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

# Base name for source image artifacts (extension will be added based on upload)
SOURCE_IMAGE_BASE = "source_image"
SOURCE_IMAGE_STATE_KEY = "current_source_image_filename"


def get_extension_from_mime(mime_type: str) -> str:
    """
    Convert MIME type to file extension.
    
    Args:
        mime_type: MIME type string (e.g., 'image/jpeg')
    
    Returns:
        File extension with dot (e.g., '.jpg')
    """
    mime_to_ext = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'image/bmp': '.bmp',
        'image/tiff': '.tiff',
        'image/svg+xml': '.svg',
    }
    return mime_to_ext.get(mime_type.lower(), '.png')  # Default to .png if unknown


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
    info.append("\n--- SAVED SOURCE IMAGE ARTIFACT ---")
    current_source_filename = tool_context.state.get(SOURCE_IMAGE_STATE_KEY)
    if current_source_filename:
        info.append(f"Current source image filename: {current_source_filename}")
        try:
            saved_image = await tool_context.load_artifact(current_source_filename)
            if saved_image:
                info.append(f"✅ Source image artifact EXISTS")
                if hasattr(saved_image, 'inline_data') and saved_image.inline_data:
                    info.append(f"   MIME type: {saved_image.inline_data.mime_type}")
                    data_size = len(saved_image.inline_data.data)
                    info.append(f"   Size: {data_size:,} bytes")
            else:
                info.append(f"❌ Could not load source image artifact")
        except Exception as e:
            info.append(f"❌ Error loading source image: {str(e)}")
    else:
        info.append(f"❌ No source image filename stored in state")
    
    # Check state
    info.append("\n--- SESSION STATE ---")
    info.append(f"State keys: {list(tool_context.state.keys())}")
    for key, value in tool_context.state.items():
        if isinstance(value, (str, int, float, bool)):
            info.append(f"  {key}: {value}")
    
    # Check other possible locations for uploaded content
    info.append("\n--- OTHER ATTRIBUTES ---")
    possible_attrs = ['message', 'current_turn', 'session', 'invocation_id']
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
    Each new upload creates a new version of the artifact.
    The image filename preserves the original file extension.
    
    Returns:
        str: Success or error message
    """
    try:
        # Look for uploaded image in user_content
        if not tool_context.user_content or not tool_context.user_content.parts:
            return "❌ No image found. Please upload a photo first!"
        
        image_found = False
        for part in tool_context.user_content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                # Get the correct extension from MIME type
                extension = get_extension_from_mime(part.inline_data.mime_type)
                artifact_filename = f"{SOURCE_IMAGE_BASE}{extension}"
                
                # Create artifact with original MIME type and extension
                image_artifact = types.Part(
                    inline_data=types.Blob(
                        mime_type=part.inline_data.mime_type,
                        data=part.inline_data.data
                    )
                )
                
                # Save the artifact (this automatically creates a new version if filename exists)
                version = await tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=image_artifact
                )
                
                # Store the current source image filename in state
                tool_context.state[SOURCE_IMAGE_STATE_KEY] = artifact_filename
                
                image_found = True
                print(f"✅ Saved source image as: {artifact_filename} (version {version})")
                print(f"   MIME type: {part.inline_data.mime_type}")
                
                return f"✅ Perfect! I've saved your photo as {artifact_filename} (version {version}). Now I can transform it into different Halloween characters without you needing to upload it again!"
        
        if not image_found:
            return "❌ No image found in your message. Please attach a photo!"
            
    except Exception as e:
        import traceback
        return f"Error saving image: {str(e)}\n{traceback.format_exc()}"


async def check_for_source_image(tool_context: ToolContext) -> str:
    """
    Check if there's a saved source image or a newly uploaded image.
    Always uses the latest version of the saved image.
    
    Returns:
        str: Status message about image availability
    """
    try:
        # First check if there's a saved artifact (latest version)
        current_source_filename = tool_context.state.get(SOURCE_IMAGE_STATE_KEY)
        if current_source_filename:
            try:
                # Load without version parameter to get the latest version
                saved_image = await tool_context.load_artifact(current_source_filename)
                if saved_image:
                    return f"✅ Source image is ready ({current_source_filename}, latest version)! You can request any Halloween character transformation."
            except Exception as e:
                print(f"Error loading saved image: {e}")
        
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
    Always uses the latest version of the saved source image.
    Falls back to newly uploaded image if no saved image exists.
    
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
        # STRATEGY 1: Try to load the saved source image artifact (latest version)
        current_source_filename = tool_context.state.get(SOURCE_IMAGE_STATE_KEY)
        if current_source_filename:
            try:
                # Load without version parameter to automatically get the latest version
                saved_image = await tool_context.load_artifact(current_source_filename)
                if saved_image and hasattr(saved_image, 'inline_data') and saved_image.inline_data:
                    image_part = types.Part(
                        inline_data=types.Blob(
                            mime_type=saved_image.inline_data.mime_type,
                            data=saved_image.inline_data.data
                        )
                    )
                    contents.append(image_part)
                    image_found = True
                    image_source = f"saved artifact ({current_source_filename}, latest version)"
                    print(f"✅ Using saved source image: {current_source_filename} (latest version)")
            except Exception as e:
                print(f"Could not load saved artifact, checking user_content: {e}")
        
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
        
        print(f"🎃 Generating {character_type} transformation using {image_source}...")
        
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
    Clears the saved source image reference from state.
    The next uploaded image will become the new source image.
    
    Returns:
        str: Confirmation message
    """
    try:
        if SOURCE_IMAGE_STATE_KEY in tool_context.state:
            old_filename = tool_context.state[SOURCE_IMAGE_STATE_KEY]
            del tool_context.state[SOURCE_IMAGE_STATE_KEY]
            return f"✅ Cleared reference to {old_filename}. Ready for a new photo! Just upload a new image and I'll save it as the new source."
        else:
            return "✅ No source image was set. Ready for you to upload a photo!"
    except Exception as e:
        return f"Error: {str(e)}"


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Creates Halloween characters and transforms photos into spooky personas. Preserves image format and supports versioning.",
    instruction="""You are a Halloween Character Transformer with intelligent image management.

🔍 DEBUG MODE:
- When user says "debug", call 'debug_context' to show system information

📸 IMAGE MANAGEMENT:
- Uploaded images are saved with their original extension (.jpg, .png, .gif, etc.)
- Each new upload creates a new VERSION of the source image
- The system ALWAYS uses the LATEST version automatically
- Users can upload new photos anytime - they replace the previous one

🎃 TRANSFORMATION WORKFLOW:

STEP 1: IMAGE UPLOAD
- When user uploads an image, IMMEDIATELY call 'save_uploaded_image'
- This saves it with proper extension and versioning
- Confirm: "Great! I've saved your [extension] photo (version X)"

STEP 2: CHARACTER SELECTION
- Ask user for preferences or offer to surprise them
- Character types: """ + ", ".join(HALLOWEEN_CHARACTERS) + """
- Create vivid backstory (2-3 sentences):
  * Origin story
  * Supernatural powers
  * Terrifying features

STEP 3: TRANSFORMATION
- Call 'transform_to_halloween_character' with detailed description
- The tool automatically uses the latest version of the saved image
- Remind user: "Want another character? Just ask - no need to re-upload!"

🔄 MULTIPLE TRANSFORMATIONS:
- For second, third, fourth transformations: just ask for new character
- Call 'transform_to_halloween_character' directly
- System automatically uses the latest saved image
- User can try unlimited characters without re-uploading

📤 NEW PHOTO:
- If user uploads a new photo, call 'save_uploaded_image'
- This creates a NEW VERSION automatically
- Confirm: "Got your new photo (version X)! Ready for transformations."

🎯 CHARACTER DESCRIPTION REQUIREMENTS:
Must include:
- Skin tone/texture with specific colors
- Eye characteristics (color, glow, shape)
- Hair style and color
- Clothing style and colors with details
- Special features (fangs, scars, etc.)
- Atmospheric elements (fog, lighting, background)
- Overall mood and color palette

Example:
"Pale grey-blue skin with visible veins, glowing amber eyes with reptilian pupils, long matted black hair with silver streaks, tattered Victorian mourning dress in deep purple and black with cobweb lace, elongated fingers with black nails, surrounded by swirling green mist and moonlit graveyard atmosphere with twisted trees"

🗑️ RESET:
- If user wants to clear the current image: call 'clear_source_image'
- Then they can upload a fresh photo

🦇 Let's create terrifying transformations! 💀🎃
""",
    tools=[
        debug_context,
        save_uploaded_image,
        check_for_source_image,
        transform_to_halloween_character,
        clear_source_image
    ],
)