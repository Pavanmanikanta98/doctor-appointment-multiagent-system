def clean_messages(messages):
    """Smartly reduce messages while keeping identity, latest context, and decision cues."""
    if not messages:
        return []

    kept = []
    seen_keys = set()

    for msg in reversed(messages):  # Reverse to keep latest relevant
        key = f"{msg.content[:100]}_{type(msg).__name__}"

        # Always keep:
        if (
            "identification number is" in msg.content.lower()
            or "id_number" in getattr(msg, "content", "").lower()
            or "reasoning" in msg.content.lower()
            or "routing to" in msg.content.lower()
        ):
            kept.append(msg)
            continue

        if key not in seen_keys:
            seen_keys.add(key)
            kept.append(msg)

    return list(reversed(kept))  # Restore original order




def generate_confirmation_context(last_ai_content: str, reasoning: str) -> str:
    """Generate context message for confirmation node"""
    
    if "available" in last_ai_content.lower() and "book" in reasoning.lower():
        return "I found some available appointment slots for you. Let me get your confirmation to proceed with the booking."
    
    elif "?" in last_ai_content:
        return "I need your input to help you better. Please provide your response to continue."
    
    else:
        return "I need to confirm some details with you before we can proceed further."