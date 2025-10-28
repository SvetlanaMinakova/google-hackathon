from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext
import google.genai.types as types
from google import genai
import uuid
import random
from datetime import datetime


# Halloween character types for random selection
HALLOWEEN_CHARACTERS = [
    "vampire", "witch", "zombie", "werewolf", "ghost", "mummy", "skeleton",
    "devil", "pumpkin-headed creature", "shadow demon", "cursed clown",
    "bloodied bride", "possessed doll", "ancient sorcerer", "wailing banshee"
]

# State keys for image management
UPLOADED_IMAGES_KEY = "uploaded_images_history"  # List of all uploaded images
CURRENT_IMAGE_INDEX_KEY = "current_image_index"  # Index of the most recent image


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
    Debug tool to explore the ToolContext structure and uploaded images history.
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
    
    # Check uploaded images history
    info.append("\n--- UPLOADED IMAGES HISTORY ---")
    uploaded_images = tool_context.state.get(UPLOADED_IMAGES_KEY, [])
    current_index = tool_context.state.get(CURRENT_IMAGE_INDEX_KEY)
    
    if uploaded_images:
        info.append(f"Total uploaded images: {len(uploaded_images)}")
        info.append(f"Current/Latest image index: {current_index}")
        info.append("\nImage History:")
        for img in uploaded_images:
            marker = " ← LATEST" if img.get('index') == current_index else ""
            info.append(f"  #{img.get('index')}: {img.get('filename')} ({img.get('mime_type')}){marker}")
            info.append(f"      Uploaded: {img.get('timestamp', 'unknown')}")
    else:
        info.append("No images uploaded yet")
    
    # Check state
    info.append("\n--- SESSION STATE ---")
    info.append(f"State keys: {list(tool_context.state.keys())}")
    
    info.append("\n" + "=" * 60)
    
    return "\n".join(info)


async def save_uploaded_image(tool_context: ToolContext) -> str:
    """
    Saves the uploaded image to the history array.
    Each upload gets a unique index and is stored as a separate artifact.
    
    Returns:
        str: Success or error message
    """
    try:
        # Look for uploaded image in user_content
        if not tool_context.user_content or not tool_context.user_content.parts:
            return "❌ No image found. Please upload a photo first!"
        
        # Get or initialize the uploaded images history
        uploaded_images = tool_context.state.get(UPLOADED_IMAGES_KEY, [])
        
        # Determine the next index
        next_index = 1 if not uploaded_images else max(img['index'] for img in uploaded_images) + 1
        
        image_found = False
        for part in tool_context.user_content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                # Get the correct extension from MIME type
                extension = get_extension_from_mime(part.inline_data.mime_type)
                artifact_filename = f"source_image_{next_index}{extension}"
                
                # Create artifact with original MIME type and extension
                image_artifact = types.Part(
                    inline_data=types.Blob(
                        mime_type=part.inline_data.mime_type,
                        data=part.inline_data.data
                    )
                )
                
                # Save the artifact
                version = await tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=image_artifact
                )
                
                # Add to history
                image_info = {
                    'index': next_index,
                    'filename': artifact_filename,
                    'mime_type': part.inline_data.mime_type,
                    'timestamp': datetime.now().isoformat(),
                    'version': version
                }
                uploaded_images.append(image_info)
                
                # Update state
                tool_context.state[UPLOADED_IMAGES_KEY] = uploaded_images
                tool_context.state[CURRENT_IMAGE_INDEX_KEY] = next_index
                
                image_found = True
                print(f"✅ Saved image #{next_index} as: {artifact_filename}")
                print(f"   Total images in history: {len(uploaded_images)}")
                
                return f"✅ Perfect! I've saved your photo as image #{next_index} ({artifact_filename}). You now have {len(uploaded_images)} image(s) in your collection. I can transform any of them - just specify which one, or I'll use the latest!"
        
        if not image_found:
            return "❌ No image found in your message. Please attach a photo!"
            
    except Exception as e:
        import traceback
        return f"Error saving image: {str(e)}\n{traceback.format_exc()}"


async def list_uploaded_images(tool_context: ToolContext) -> str:
    """
    Lists all uploaded images in the history.
    
    Returns:
        str: Formatted list of all uploaded images
    """
    try:
        uploaded_images = tool_context.state.get(UPLOADED_IMAGES_KEY, [])
        current_index = tool_context.state.get(CURRENT_IMAGE_INDEX_KEY)
        
        if not uploaded_images:
            return "❌ No images uploaded yet. Upload a photo to get started!"
        
        result = [f"📸 You have {len(uploaded_images)} image(s) in your collection:\n"]
        
        for img in uploaded_images:
            index = img.get('index')
            filename = img.get('filename')
            timestamp = img.get('timestamp', 'unknown time')
            
            marker = " ⭐ (latest)" if index == current_index else ""
            result.append(f"#{index}: {filename}{marker}")
            result.append(f"   Uploaded: {timestamp}")
        
        result.append(f"\n💡 To transform a specific image, just say 'transform image #2 into a vampire' or similar!")
        result.append(f"💡 If you don't specify, I'll use the latest image (#{current_index}).")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error listing images: {str(e)}"


async def check_for_source_image(tool_context: ToolContext) -> str:
    """
    Check if there are saved images or a newly uploaded image.
    
    Returns:
        str: Status message about image availability
    """
    try:
        # Check uploaded images history
        uploaded_images = tool_context.state.get(UPLOADED_IMAGES_KEY, [])
        if uploaded_images:
            count = len(uploaded_images)
            current_index = tool_context.state.get(CURRENT_IMAGE_INDEX_KEY)
            return f"✅ You have {count} image(s) saved! Latest is image #{current_index}. Ready for transformations!"
        
        # Check if there's a newly uploaded image in user_content
        if tool_context.user_content and tool_context.user_content.parts:
            for part in tool_context.user_content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith('image/'):
                    return "✅ New image detected! I'll save it to your collection so we can use it for transformations."
        
        return "❌ No images available. Please upload a photo to get started with Halloween transformations!"
        
    except Exception as e:
        return f"Error checking for images: {str(e)}"


async def transform_to_halloween_character(
    character_type: str,
    character_description: str,
    tool_context: ToolContext,
    image_number: int | None = None
) -> str:
    """
    Transform a photo into a specified Halloween character.
    Can transform a specific image by number, or defaults to the latest image.
    
    Args:
        character_type (str): Type of Halloween character (e.g., "vampire", "zombie")
        character_description (str): Detailed description of how the transformation should look
        tool_context (ToolContext): ADK tool context
        image_number (int | None): Specific image number to transform (e.g., 2 for "image #2").
                                    If None, uses the latest image.
    
    Returns:
        str: Success message or error description
    """
    client = genai.Client()
    contents = []
    image_found = False
    image_source = None
    
    try:
        uploaded_images = tool_context.state.get(UPLOADED_IMAGES_KEY, [])
        current_index = tool_context.state.get(CURRENT_IMAGE_INDEX_KEY)
        
        # Determine which image to use
        target_index = image_number if image_number is not None else current_index
        
        if not uploaded_images:
            # No saved images, check for newly uploaded image
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
        else:
            # Try to find the requested image in history
            target_image = None
            for img in uploaded_images:
                if img['index'] == target_index:
                    target_image = img
                    break
            
            if not target_image:
                available_indices = [img['index'] for img in uploaded_images]
                return f"❌ Image #{target_index} not found. Available images: {', '.join(f'#{i}' for i in available_indices)}"
            
            # Load the target image
            try:
                saved_image = await tool_context.load_artifact(target_image['filename'])
                if saved_image and hasattr(saved_image, 'inline_data') and saved_image.inline_data:
                    image_part = types.Part(
                        inline_data=types.Blob(
                            mime_type=saved_image.inline_data.mime_type,
                            data=saved_image.inline_data.data
                        )
                    )
                    contents.append(image_part)
                    image_found = True
                    image_source = f"image #{target_index} ({target_image['filename']})"
                    print(f"✅ Using {image_source}")
                else:
                    return f"❌ Could not load image #{target_index}"
            except Exception as e:
                return f"❌ Error loading image #{target_index}: {str(e)}"
        
        if not image_found:
            return "❌ No image available. Please upload a photo first!"
        
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
                artifact_filename = f"halloween_{safe_character_name}_img{target_index}_{uuid.uuid4().hex[:8]}.png"
                
                await tool_context.save_artifact(
                    filename=artifact_filename,
                    artifact=image_artifact
                )
                
                image_ref = f"image #{target_index}" if image_number else "your latest image"
                total_images = len(uploaded_images)
                
                suggestion = ""
                if total_images > 1:
                    suggestion = f"\n\n💡 You have {total_images} images. Want to try transforming a different one? Just say 'transform image #X into a [character]'!"
                elif total_images == 0:
                    suggestion = "\n\n💡 Upload more photos to try different transformations!"
                
                return f"🎃 Successfully transformed {image_ref} into a terrifying {character_type}! Check out your spooky new look above!{suggestion}"
        
        return "Image generation completed but no image was returned. This might be due to safety filters."
        
    except Exception as e:
        import traceback
        return f"Error during transformation: {str(e)}\n\nDetails: {traceback.format_exc()}"


async def clear_image_history(tool_context: ToolContext) -> str:
    """
    Clears all uploaded images from history.
    
    Returns:
        str: Confirmation message
    """
    try:
        uploaded_images = tool_context.state.get(UPLOADED_IMAGES_KEY, [])
        count = len(uploaded_images)
        
        if count > 0:
            # Clear the state
            tool_context.state[UPLOADED_IMAGES_KEY] = []
            if CURRENT_IMAGE_INDEX_KEY in tool_context.state:
                del tool_context.state[CURRENT_IMAGE_INDEX_KEY]
            
            return f"✅ Cleared {count} image(s) from history. Ready for fresh uploads!"
        else:
            return "✅ No images to clear. Ready for you to upload photos!"
    except Exception as e:
        return f"Error: {str(e)}"


root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="Creates Halloween characters and transforms photos. Maintains history of all uploaded images for flexible transformations.",
    instruction="""You are a Halloween Character Transformer with advanced image history management.

🔍 DEBUG MODE:
- When user says "debug", call 'debug_context' to show system information

📸 IMAGE HISTORY SYSTEM:
- Every uploaded image is saved with a unique number (#1, #2, #3, etc.)
- Users can transform ANY previously uploaded image by number
- If no number specified, use the LATEST image
- Call 'list_uploaded_images' to show all available images

🎃 WORKFLOW:

STEP 1: IMAGE UPLOAD
- When user uploads an image, IMMEDIATELY call 'save_uploaded_image'
- Confirm: "Saved as image #X! You now have Y images in your collection."

STEP 2: SHOW AVAILABLE IMAGES (if user asks)
- Call 'list_uploaded_images' to show all images with their numbers
- Explain they can reference any image by number

STEP 3: TRANSFORMATION
- If user says "transform image #2 into a vampire":
  * Extract the number: 2
  * Call transform_to_halloween_character with image_number=2
- If user says "transform me into a zombie" (no number):
  * Call transform_to_halloween_character with image_number=None (uses latest)
- If user uploads multiple images and asks for transformation:
  * Ask which image they want transformed, or offer to use the latest

🎯 CHARACTER TYPES:
""" + ", ".join(HALLOWEEN_CHARACTERS) + """

📝 TRANSFORMATION RULES:
When calling transform_to_halloween_character:
- ALWAYS provide image_number parameter
- If user specified a number (e.g., "second image", "image 3", "#2"): extract it and pass it
- If no number specified: pass image_number=None (uses latest)

Examples of extracting image numbers:
- "transform the second picture" → image_number=2
- "use image #3" → image_number=3  
- "transform the first one" → image_number=1
- "make me a vampire" → image_number=None (latest)

🎨 CHARACTER DESCRIPTIONS must include:
- Skin tone/texture with specific colors
- Eye characteristics (color, glow, shape)
- Hair style and color details
- Clothing style with colors and textures
- Special features (fangs, scars, claws, etc.)
- Atmospheric elements (fog, lighting, background)
- Overall mood and color palette

Example description:
"Decaying grey-green skin with visible wounds, milky white eyes with no pupils, matted blood-stained hair in patches, torn and dirty clothing hanging in shreds, exposed bones on hands and arms with blackened fingernails, surrounded by thick green fog and dark graveyard atmosphere with tombstones and dead trees"

📊 USER QUERIES TO HANDLE:
- "How many images do I have?" → call list_uploaded_images
- "Show my images" → call list_uploaded_images
- "Transform the second one" → extract number=2, call transform
- "Use my first photo as a witch" → number=1, character="witch"
- "Clear my images" → call clear_image_history

💡 HELPFUL TIPS TO SHARE:
- Mention they can upload multiple photos and transform each one differently
- Remind them they can reference any previous image by number
- If they have multiple images, suggest trying different characters on different photos

🗑️ RESET:
- If user wants to clear all images: call 'clear_image_history'

🦇 Let's create an amazing collection of spooky transformations! 💀🎃
""",
    tools=[
        debug_context,
        save_uploaded_image,
        list_uploaded_images,
        check_for_source_image,
        transform_to_halloween_character,
        clear_image_history
    ],
)