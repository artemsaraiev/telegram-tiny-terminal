import requests
from typing import List, Dict
import sys
import time
import json

global_context: List[Dict] = []

def show_global_context() -> str:
    """Display the current global context"""
    if not global_context:
        return "Context is empty"
    
    context_text = "\nCurrent context:"
    context_text += f"\nTotal messages: {len(global_context)}\n"
    context_text += "-" * 40 + "\n"
    
    for msg in global_context:
        context_text += f"[{msg['date']}] {msg['sender']}: {msg['text']}\n"
    
    context_text += "-" * 40
    return context_text

async def process_prompt_with_context(prompt: str) -> str:
    """Process a prompt with the global context using Ollama with streaming"""
    try:
        url = "http://localhost:11434/api/generate"
        
        context_text = "\n".join([
            f"[{msg['date']}] {msg['sender']}: {msg['text']}"
            for msg in global_context
        ])
        
        full_prompt = f"""Previous context:
        {context_text}

        User question:
        {prompt}

        Please provide a response taking into account the context above."""
        
        data = {
            "model": "llama2",
            "prompt": full_prompt,
            "stream": True
        }
        
        response = requests.post(url, json=data, stream=True)
        response.raise_for_status()
        
        # Process the streaming response
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    json_response = json.loads(line.decode('utf-8'))
                    if 'error' in json_response:
                        return f"Error from API: {json_response['error']}"
                    if 'response' in json_response:
                        chunk = json_response['response']
                        full_response += chunk
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                        time.sleep(0.01)
                except json.JSONDecodeError as e:
                    print(f"\nWarning: Could not decode response: {str(e)}")
                    continue
                except Exception as e:
                    print(f"\nWarning: Error processing chunk: {str(e)}")
                    continue
        
        print()  # New line at the end
        return full_response
    except requests.exceptions.RequestException as e:
        return f"Network error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


async def add_messages_to_context(formatted_messages: List[Dict]) -> str:
    """Add formatted messages to global context"""
    global global_context
    
    try:
        for msg in formatted_messages:
            if msg:  # Only add non-None messages
                global_context.append(msg)
        
        return f"Added {len(formatted_messages)} messages to context. Total context size: {len(global_context)} messages"
    except Exception as e:
        return f"Error adding to context: {str(e)}"

def clear_global_context() -> str:
    """Clear the global context"""
    global global_context
    context_size = len(global_context)
    global_context = []
    return f"Cleared {context_size} messages from context"

async def get_llm_summary(messages_text: str) -> str:
    """Get a summary using local Ollama API"""
    try:
        url = "http://localhost:11434/api/generate"
        
        prompt = f"""Below are messages from a Telegram chat. 
        Please provide a brief, clear summary of the main discussion points:

        {messages_text}
        """
        
        data = {
            "model": "llama2",
            "prompt": prompt,
            "stream": True
        }
        
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()['response']
    except Exception as e:
        return f"Error getting LLM summary: {str(e)}"