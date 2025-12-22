"""
Fixed Pharmacy Agent with Debug Timing
"""

import os
import json
import time
from typing import List, Dict, Any, Generator, Optional
from openai import OpenAI
from tools import TOOLS, execute_tool
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini")  # ⚠️ בדוק שזה לא gpt-5!

SYSTEM_PROMPT = """You are a pharmacy information assistant for a retail pharmacy chain in Israel.
You provide factual medication information — NOT medical advice.

CAPABILITIES:
• Medication facts (ingredients, dosage, usage)
• Stock availability & prescription requirements
• Search by ingredient & prescription management
• Drug interaction checks & allergy verification
• Reserve medications for pickup

STRICT BOUNDARIES:
• No medical advice, diagnoses, or treatment recommendations
• No "should I take X" answers
• If symptoms are described → respond ONLY with a brief refusal and redirection.

REFUSAL TEMPLATE:
"I can provide medication information, but I can't give medical advice. Please consult a pharmacist or doctor."

RESPONSE FORMAT:
Adapt to the question (lists, single-item info, or direct answers).
Use clear structure and minimal emojis (💊 ✅ ⚠️).
Match the user's language (Hebrew/English).

TOOL USAGE (CRITICAL):
• For medication inquiries - ALWAYS call the relevant tool
• NEVER answer from general knowledge
• If tool returns no result → "I can provide information only for products available in the system."

SAFETY:
Always check allergies if user_id is known.
When in doubt — refuse and redirect."""


class PharmacyAgent:
    """Pharmacy agent with streaming and debug timing"""
    
    def __init__(self, model: str = MODEL, debug: bool = False):
        self.model = model
        self.client = client
        self.debug = debug
    
    def _log(self, msg: str):
        """Debug logging"""
        if self.debug:
            print(f"[AGENT] {msg}")
    
    def chat(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
        """Main chat method with streaming"""
        
        t_start = time.time()
        self._log(f"Chat started with model: {self.model}")
        
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        
        # First API call
        t_api = time.time()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            tools=TOOLS,
            tool_choice="auto",
            stream=True,
            temperature=0.1  # Faster decisions
        )
        self._log(f"API call initiated: {(time.time() - t_api)*1000:.0f}ms")
        
        if stream:
            yield from self._handle_streaming_response(response, full_messages, t_start)
        else:
            yield from self._handle_non_streaming_response(response, full_messages)
    
    def _handle_streaming_response(
        self, 
        response, 
        messages: List[Dict[str, str]],
        t_start: float
    ) -> Generator[Dict[str, Any], None, None]:
        """Handle streaming response with tool calls"""
        
        assistant_message = {"role": "assistant", "content": "", "tool_calls": []}
        current_tool_call = None
        tool_call_index = -1
        first_chunk_time = None
        chunk_count = 0
        
        # Stream first response
        for chunk in response:
            if not chunk.choices:
                continue
            
            if first_chunk_time is None:
                first_chunk_time = time.time()
                self._log(f"⚡ First chunk: {(first_chunk_time - t_start)*1000:.0f}ms")
            
            chunk_count += 1
            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason
            
            # Text content
            if delta.content:
                assistant_message["content"] += delta.content
                if self.debug and chunk_count <= 5:
                    self._log(f"Chunk #{chunk_count}: '{delta.content[:30]}'")
                yield {
                    "type": "text",
                    "content": delta.content
                }
            
            # Tool calls
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    if tool_call_delta.index != tool_call_index:
                        if current_tool_call:
                            assistant_message["tool_calls"].append(current_tool_call)
                        
                        tool_call_index = tool_call_delta.index
                        current_tool_call = {
                            "id": tool_call_delta.id or f"call_{tool_call_index}",
                            "type": "function",
                            "function": {
                                "name": tool_call_delta.function.name or "",
                                "arguments": ""
                            }
                        }
                    
                    if tool_call_delta.function.arguments:
                        current_tool_call["function"]["arguments"] += tool_call_delta.function.arguments
            
            # Finish reason
            if finish_reason == "tool_calls":
                if current_tool_call:
                    assistant_message["tool_calls"].append(current_tool_call)
                
                if not assistant_message["content"]:
                    assistant_message.pop("content", None)
                
                self._log(f"Tool calls detected: {len(assistant_message['tool_calls'])} tools")
                yield from self._execute_and_continue(messages, assistant_message, t_start)
                return
            
            elif finish_reason == "stop":
                self._log(f"✅ Completed in {(time.time() - t_start)*1000:.0f}ms ({chunk_count} chunks)")
                return
    
    def _handle_non_streaming_response(
        self, 
        response, 
        messages: List[Dict[str, str]]
    ) -> Generator[Dict[str, Any], None, None]:
        """Handle non-streaming response"""
        message = response.choices[0].message
        
        if message.content:
            yield {"type": "text", "content": message.content}
        
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
            
            yield from self._execute_and_continue(messages, assistant_message, time.time())
    
    def _execute_and_continue(
        self, 
        messages: List[Dict[str, str]], 
        assistant_message: Dict[str, Any],
        t_start: float
    ) -> Generator[Dict[str, Any], None, None]:
        """Execute ALL tools then continue conversation ONCE"""
        
        messages.append(assistant_message)
        
        # Execute each tool call
        for tool_call in assistant_message["tool_calls"]:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            
            yield {
                "type": "tool_call",
                "tool_name": function_name,
                "arguments": function_args,
                "tool_call_id": tool_call["id"]
            }
            
            # Execute tool with timing
            t_tool = time.time()
            result = execute_tool(function_name, function_args)
            tool_time = (time.time() - t_tool) * 1000
            
            if tool_time > 100:
                self._log(f"⚠️ SLOW TOOL: {function_name} took {tool_time:.0f}ms")
            else:
                self._log(f"Tool {function_name}: {tool_time:.0f}ms")
            
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
        
        # ✅ Now call LLM ONCE with all tool results
        self._log("Calling LLM with tool results...")
        t_final = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True  # ⚡ CRITICAL
        )
        
        first_final_chunk = None
        
        # Stream final response
        for chunk in response:
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            
            if delta.content:
                if first_final_chunk is None:
                    first_final_chunk = time.time()
                    self._log(f"⚡ Final response first chunk: {(first_final_chunk - t_final)*1000:.0f}ms")
                
                yield {
                    "type": "text",
                    "content": delta.content
                }
        
        self._log(f"✅ Total time: {(time.time() - t_start)*1000:.0f}ms")


# Convenience functions
def chat_streaming(user_message: str, history: List[Dict[str, str]] = None, user_id: Optional[str] = None, debug: bool = False) -> Generator:
    """Convenience function for streaming chat"""
    agent = PharmacyAgent(debug=debug)
    messages = history or []
    
    if user_id:
        messages.append({
            "role": "system",
            "content": f"Customer ID: {user_id}. Fetch prescriptions and relevant info for this user."
        })

    messages.append({"role": "user", "content": user_message})
    yield from agent.chat(messages, stream=True)


def chat_complete(user_message: str, history: List[Dict[str, str]] = None) -> str:
    """Complete (non-streaming) chat"""
    result = []
    for chunk in chat_streaming(user_message, history):
        if chunk["type"] == "text":
            result.append(chunk["content"])
    return "".join(result)


# Testing
if __name__ == "__main__":
    print("=" * 70)
    print("PHARMACY AGENT - DEBUG TEST")
    print("=" * 70)
    
    print("\n🧪 TEST: Medication inquiry with timing")
    print("-" * 70)
    print("User: Tell me about Acamol\n")
    
    for chunk in chat_streaming("Tell me about Acamol", debug=True):
        if chunk["type"] == "text":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_call":
            print(f"\n[🔧 {chunk['tool_name']}]", flush=True)
    
    print("\n" + "=" * 70)