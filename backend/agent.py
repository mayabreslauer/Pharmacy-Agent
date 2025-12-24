"""
Pharmacy Agent 
"""

import os
import json
from typing import List, Dict, Any, Generator, Optional, Union
from openai import OpenAI
from tools import TOOLS, execute_tool
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-5")

SYSTEM_PROMPT = """You are a pharmacy information assistant for a retail pharmacy chain.
Provide factual medication information — NOT medical advice.

CAPABILITIES:
✅ Medication info (ingredients, dosage, usage, side effects)
✅ Stock availability & prescription requirements
✅ Check allergies & interactions only during reservation/ordering with user_id.
✅ Reserve medications for pickup

BOUNDARIES:
🚫 No medical advice or diagnoses
🚫 If symptoms described → "I provide medication information, not medical advice. Please consult a pharmacist or doctor." (in user's language)
🚫 Never use user_id tools unless user_id explicitly provided

TOOLS:
• Use tools for ALL queries requiring current data
• Understand context: "it" / "this medication" refers to previously mentioned items
• No user_id? Don't call user-specific tools

ALLERGIES (CRITICAL):
• If allergy detected → State the fact: "You have a recorded allergy to [ingredient]"
• Cannot reserve: "I cannot reserve this medication for you"
• Redirect: "For alternative options, please consult a pharmacist or doctor"
• DO NOT suggest alternatives or say "use X instead"
• If user asks about allergies without ordering: I provide medication information only, not personal allergy checks. Please consult a pharmacist or doctor.

RESERVATIONS (IMPORTANT):
When the user wants to reserve/order a medication (in any language) and provides user_id:
1. Check allergies (if user_id is available) and return the result to the user.
2. Check if its in stock and if prescription needed - and act apropriatly.
2. Ask the user if they want to continue with the purchase.
3. Only if the user confirms, use the reserve_medication tool with all collected details (medication name, quantity, user_id).

FORMAT:
• Lists for multiple items
• Structured info for single medications
• Direct answers for simple questions
• Use 💊 ✅ ⚠️ emojis sparingly

STREAMING:
Start streaming your answer as soon as possible ONLY WITH DATA FROM THE DATABASE, even while still reasoning - dont answer too long.
Do not wait to complete all reasoning before sending the first tokens.
Do not add any information beyond what is provided in the medications database,
the user database, and the system instructions.

SAFETY:
Always check allergies if user_id is known.
When in doubt — refuse and redirect."""



class PharmacyAgent:
    """Pharmacy agent compatible with both API styles"""
    
    def __init__(self, model: str = MODEL, debug: bool = False):
        self.model = model
        self.client = client
        self.debug = debug
    
    def _log(self, msg: str):
        if self.debug:
            print(f"[AGENT] {msg}")
    
    def chat(
        self, 
        messages: Optional[List[Dict[str, str]]] = None,
        user_message: Optional[str] = None,
        user_id: Optional[str] = None,
        stream: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """
        ✅ FLEXIBLE: Supports both API styles!
        
        Style 1 (NEW - for tests):
            agent.chat(messages=[...], stream=True)
        
        Style 2 (OLD - for UI/API):
            agent.chat(user_message="...", user_id="...", stream=True)
        
        Args:
            messages: Conversation history (NEW style)
            user_message: Single message (OLD style)
            user_id: Optional user ID (OLD style)
            stream: Whether to stream responses
            
        Yields:
            Response chunks
        """
        # ✅ Convert OLD style to NEW style
        if user_message is not None and messages is None:
            self._log("Converting old API style to new")
            messages = []
            
            if user_id:
                messages.append({
                    "role": "system",
                    "content": f"Customer ID: {user_id}. Fetch prescriptions and relevant info for this user."
                })
            
            messages.append({"role": "user", "content": user_message})
        
        # ✅ Validate we have messages
        if messages is None:
            raise ValueError("Either 'messages' or 'user_message' must be provided")
        
        # Add system prompt at the beginning if not present
        if not messages or messages[0].get("role") != "system":
            full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        else:
            full_messages = messages
        
        self._log(f"Chat with {len(full_messages)} messages")
        
        # First API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            tools=TOOLS,
            tool_choice="auto",
            stream=True,
        )
        
        if stream:
            yield from self._handle_streaming_response(response, full_messages)
        else:
            yield from self._handle_non_streaming_response(response, full_messages)
    
    def _handle_streaming_response(
    self, 
    response, 
    messages: List[Dict[str, str]]
) -> Generator[Dict[str, Any], None, None]:
        """
        Handle streaming response from GPT-5, including tool calls.
        Ensures clean text streaming without gibberish when tools are called.
        """

        assistant_message = {"role": "assistant", "content": "", "tool_calls": []}
        current_tool_call = None
        tool_call_index = -1
        buffer_text = ""  # buffer for text chunks before tool calls

        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            # --- accumulate text ---
            if delta.content:
                buffer_text += delta.content
                yield {"type": "text", "content": delta.content}

            # --- handle tool calls ---
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    if tool_call_delta.index != tool_call_index:
                        # flush previous tool call
                        if current_tool_call:
                            assistant_message["tool_calls"].append(current_tool_call)

                        tool_call_index = tool_call_delta.index
                        current_tool_call = {
                            "id": tool_call_delta.id or f"call_{tool_call_index}",
                            "type": "function",
                            "function": {"name": tool_call_delta.function.name or "", "arguments": ""}
                        }

                    if tool_call_delta.function.arguments:
                        current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments

            # --- finish_reason: tool_calls ---
            if finish_reason == "tool_calls":
                # flush last tool call
                if current_tool_call:
                    assistant_message["tool_calls"].append(current_tool_call)
                # flush buffer text to assistant_message
                if buffer_text:
                    assistant_message["content"] = buffer_text
                    buffer_text = ""
                # execute tools
                yield from self._execute_and_continue(messages, assistant_message)
                return

            # --- finish_reason: stop ---
            elif finish_reason == "stop":
                if buffer_text:
                    assistant_message["content"] = buffer_text
                    buffer_text = ""
                return


    def _handle_non_streaming_response(
        self, 
        response, 
        messages: List[Dict[str, str]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Handle non-streaming response"""
        
        message = response.choices[0].message
        
        if message.content:
            yield {
                "type": "text",
                "content": message.content
            }
        
        if message.tool_calls:
            assistant_message = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            }
            
            if message.content:
                assistant_message["content"] = message.content
            
            yield from self._execute_and_continue(messages, assistant_message)
    
    def _execute_and_continue(
        self, 
        messages: List[Dict[str, str]], 
        assistant_message: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        """Execute ALL tools then call LLM ONCE"""
        
        messages.append(assistant_message)
        
        for tool_call in assistant_message["tool_calls"]:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            
            self._log(f"Executing: {function_name}({function_args})")
            
            yield {
                "type": "tool_call",
                "tool_name": function_name,
                "arguments": function_args,
                "tool_call_id": tool_call["id"]
            }
            
            result = execute_tool(function_name, function_args)
            
            self._log(f"Result: {result[:100]}...")
            
            yield {
                "type": "tool_result",
                "tool_name": function_name,
                "result": result,
                "tool_call_id": tool_call["id"]
            }
            
            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call["id"]
            })
        
        self._log("Calling LLM with tool results")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        
        for chunk in response:
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            
            if delta.content:
                yield {
                    "type": "text",
                    "content": delta.content
                }


# ========== CONVENIENCE FUNCTIONS ==========

def chat_streaming(user_message: str, history: List[Dict[str, str]] = None, user_id: Optional[str] = None) -> Generator:
    """Convenience function for streaming chat"""
    agent = PharmacyAgent()
    messages = history or []
    
    if user_id:
        messages.append({
            "role": "system",
            "content": f"Customer ID: {user_id}. Fetch prescriptions and relevant info for this user."
        })

    messages.append({"role": "user", "content": user_message})

    yield from agent.chat(messages=messages, stream=True)


def chat_complete(user_message: str, history: List[Dict[str, str]] = None) -> str:
    """Complete (non-streaming) chat"""
    result = []
    for chunk in chat_streaming(user_message, history):
        if chunk["type"] == "text":
            result.append(chunk["content"])
    return "".join(result)


# ========== TESTING ==========

if __name__ == "__main__":
    import openai
    print(openai.__version__)
    print("=" * 70)
    print("PHARMACY AGENT - COMPATIBILITY TEST")
    print("=" * 70)
    
    agent = PharmacyAgent(debug=True)
    
    # Test OLD style (for UI/API)
    print("\n🧪 TEST 1: OLD API style (user_message)")
    print("-" * 70)
    print("User: Tell me about Acamol\n")
    
    for chunk in agent.chat(user_message="Tell me about Acamol", stream=True):
        if chunk["type"] == "text":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_call":
            print(f"\n[🔧 {chunk['tool_name']}]", flush=True)
    
    # Test NEW style (for tests)
    print("\n\n🧪 TEST 2: NEW API style (messages)")
    print("-" * 70)
    print("User: Do you have Nurofen in stock?\n")
    
    messages = [{"role": "user", "content": "Do you have Nurofen in stock?"}]
    for chunk in agent.chat(messages=messages, stream=True):
        if chunk["type"] == "text":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_call":
            print(f"\n[🔧 {chunk['tool_name']}]", flush=True)
    
    print("\n\n" + "=" * 70)
    print("✅ Both API styles work!")
    print("=" * 70)
