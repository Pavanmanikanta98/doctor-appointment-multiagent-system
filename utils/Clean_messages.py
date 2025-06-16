def clean_messages(messages):
    """Remove duplicate messages and ensure proper formatting"""
    if not messages:
        return []
    
    cleaned = []
    seen_contents = set()
    
    for msg in messages:
        # Create a unique identifier based on content and type
        content_key = f"{msg.content[:100]}_{type(msg).__name__}"
        
        if content_key not in seen_contents:
            seen_contents.add(content_key)
            cleaned.append(msg)
    
    return cleaned




def generate_confirmation_context(last_ai_content: str, reasoning: str) -> str:
    """Generate context message for confirmation node"""
    
    if "available" in last_ai_content.lower() and "book" in reasoning.lower():
        return "I found some available appointment slots for you. Let me get your confirmation to proceed with the booking."
    
    elif "?" in last_ai_content:
        return "I need your input to help you better. Please provide your response to continue."
    
    else:
        return "I need to confirm some details with you before we can proceed further."