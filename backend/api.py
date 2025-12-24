# # """
# # FastAPI Server for Pharmacy Agent
# # Provides REST API endpoints for chat interaction with streaming support
# # """

# # from fastapi import FastAPI,Query, HTTPException
# # from fastapi.middleware.cors import CORSMiddleware
# # from fastapi.responses import StreamingResponse
# # from pydantic import BaseModel
# # from typing import List, Optional, Dict, Any
# # import json
# # import logging
# # from agent import PharmacyAgent
# # from database import db

# # # Configure logging
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger(__name__)

# # # Initialize FastAPI app
# # app = FastAPI(
# #     title="Pharmacy Agent API",
# #     description="AI-powered pharmacy assistant for medication information",
# #     version="1.0.0"
# # )

# # # CORS middleware for frontend
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],  # In production, specify your frontend domain
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )

# # # Initialize agent
# # agent = PharmacyAgent()

# # # ========== REQUEST/RESPONSE MODELS ==========

# # class Message(BaseModel):
# #     role: str  # "user" or "assistant"
# #     content: str

# # class ChatRequest(BaseModel):
# #     message: str
# #     history: Optional[List[Message]] = []
# #     user_id: Optional[str] = None
# #     stream: bool = True

# # class ChatResponse(BaseModel):
# #     response: str
# #     tool_calls: Optional[List[Dict[str, Any]]] = []

# # class HealthCheck(BaseModel):
# #     status: str
# #     database_status: str
# #     tools_count: int
# #     model: str

# # # ========== API ENDPOINTS ==========

# # @app.get("/", response_model=HealthCheck)
# # async def root():
# #     """Health check endpoint"""
# #     return {
# #         "status": "healthy",
# #         "database_status": "connected",
# #         "tools_count": 9,
# #         "model": agent.model
# #     }

# # @app.get("/health")
# # async def health_check():
# #     """Detailed health check"""
# #     try:
# #         # Test database
# #         test_med = db.get_medication_by_name("Acamol", "en")
# #         db_status = "healthy" if test_med else "degraded"
        
# #         return {
# #             "status": "healthy",
# #             "components": {
# #                 "api": "healthy",
# #                 "database": db_status,
# #                 "agent": "healthy"
# #             },
# #             "medications_count": len(db.medications.get("medications", [])),
# #             "users_count": len(db.users.get("users", []))
# #         }
# #     except Exception as e:
# #         logger.error(f"Health check failed: {e}")
# #         raise HTTPException(status_code=503, detail="Service unhealthy")

# # @app.post("/chat")
# # async def chat(request: ChatRequest):
# #     """
# #     Chat endpoint with streaming support
    
# #     For streaming: Returns Server-Sent Events (SSE)
# #     For non-streaming: Returns complete response
# #     """
# #     try:
# #         # Convert history to proper format
# #         messages = [{"role": msg.role, "content": msg.content} for msg in request.history]
# #         messages.append({"role": "user", "content": request.message})
        
# #         # Add user context if provided
# #         if request.user_id:
# #             # Prepend user context to first message
# #             user = db.get_user_by_id(request.user_id)
# #             if user:
# #                 user_context = f"\n[User ID: {request.user_id}, Name: {user.get('name_en')}]"
# #                 messages[0]["content"] = user_context + "\n" + messages[0]["content"]
        
# #         if request.stream:
# #             # Streaming response
# #             return StreamingResponse(
# #                 stream_chat_response(messages),
# #                 media_type="text/event-stream"
# #             )
# #         else:
# #             # Non-streaming response
# #             response_text = []
# #             tool_calls = []
            
# #             for chunk in agent.chat(messages, stream=False):
# #                 if chunk["type"] == "text":
# #                     response_text.append(chunk["content"])
# #                 elif chunk["type"] == "tool_call":
# #                     tool_calls.append({
# #                         "tool": chunk["tool_name"],
# #                         "arguments": chunk["arguments"]
# #                     })
            
# #             return ChatResponse(
# #                 response="".join(response_text),
# #                 tool_calls=tool_calls if tool_calls else None
# #             )
    
# #     except Exception as e:
# #         logger.error(f"Chat error: {e}", exc_info=True)
# #         raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
# # from fastapi.responses import StreamingResponse
# # import asyncio
# # import json

# # @app.get("/chat_sse")
# # async def chat_sse(message: str = Query(..., min_length=1), user_id: str = Query(None)):
# #     # הכנת ההודעה כ-string
# #     full_message = ""
# #     if user_id:
# #         full_message += f"[User ID: {user_id}]\n"
# #     full_message += message

# #     def event_generator():
# #         try:
# #             # שולח ל-agent הודעה אחת כ-string
# #             for chunk in agent.chat([{"role": "user", "content": full_message}], stream=True):
# #                 yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
# #             yield f"data: {json.dumps({'type': 'done'})}\n\n"
# #         except Exception as e:
# #             yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

# #     return StreamingResponse(
# #         event_generator(),
# #         media_type="text/event-stream",
# #         headers={
# #             "Cache-Control": "no-cache",
# #             "Connection": "keep-alive",
# #             "X-Accel-Buffering": "no",
# #         }
# #     )




# # async def stream_chat_response(messages: List[Dict[str, str]]):
# #     """
# #     Generator for streaming chat responses as Server-Sent Events
    
# #     Yields SSE format:
# #     data: {"type": "text", "content": "..."}\n\n
# #     """
# #     try:
# #         for chunk in agent.chat(messages, stream=True):
# #             # Format as SSE
# #             data = json.dumps(chunk, ensure_ascii=False)
# #             yield f"data: {data}\n\n"
        
# #         # Send done signal
# #         yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
# #     except Exception as e:
# #         logger.error(f"Streaming error: {e}", exc_info=True)
# #         error_data = json.dumps({
# #             "type": "error",
# #             "content": str(e)
# #         })
# #         yield f"data: {error_data}\n\n"

# # # ========== DATABASE QUERY ENDPOINTS ==========

# # @app.get("/medications")
# # async def list_medications(language: str = "en"):
# #     """Get all medications"""
# #     try:
# #         medications = db.medications.get("medications", [])
        
# #         # Format based on language
# #         formatted = []
# #         for med in medications:
# #             formatted.append({
# #                 "id": med.get("id"),
# #                 "name": med.get("name" if language == "he" else "name_en"),
# #                 "active_ingredient": med.get("active_ingredient_he" if language == "he" else "active_ingredient"),
# #                 "requires_prescription": med.get("requires_prescription"),
# #                 "in_stock": med.get("stock_quantity", 0) > 0
# #             })
        
# #         return {"medications": formatted, "count": len(formatted)}
    
# #     except Exception as e:
# #         logger.error(f"Error listing medications: {e}")
# #         raise HTTPException(status_code=500, detail="Failed to retrieve medications")

# # @app.get("/medications/{medication_name}")
# # async def get_medication(medication_name: str, language: str = "en"):
# #     """Get specific medication details"""
# #     try:
# #         med = db.get_medication_by_name(medication_name, language)
        
# #         if not med:
# #             raise HTTPException(status_code=404, detail=f"Medication '{medication_name}' not found")
        
# #         return {"medication": med}
    
# #     except HTTPException:
# #         raise
# #     except Exception as e:
# #         logger.error(f"Error getting medication: {e}")
# #         raise HTTPException(status_code=500, detail="Failed to retrieve medication")

# # @app.get("/users/{user_id}/prescriptions")
# # async def get_user_prescriptions(user_id: str, language: str = "en"):
# #     """Get user's prescriptions"""
# #     try:
# #         user = db.get_user_by_id(user_id)
# #         if not user:
# #             raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
        
# #         prescriptions = db.get_user_prescriptions(user_id)
        
# #         # Format prescriptions
# #         formatted = []
# #         for med in prescriptions:
# #             formatted.append({
# #                 "id": med.get("id"),
# #                 "name": med.get("name" if language == "he" else "name_en"),
# #                 "active_ingredient": med.get("active_ingredient_he" if language == "he" else "active_ingredient"),
# #                 "dosage": med.get("dosage_he" if language == "he" else "dosage")
# #             })
        
# #         return {
# #             "user_id": user_id,
# #             "user_name": user.get("name" if language == "he" else "name_en"),
# #             "prescriptions": formatted,
# #             "count": len(formatted)
# #         }
    
# #     except HTTPException:
# #         raise
# #     except Exception as e:
# #         logger.error(f"Error getting prescriptions: {e}")
# #         raise HTTPException(status_code=500, detail="Failed to retrieve prescriptions")

# # @app.get("/stock/{medication_name}")
# # async def check_stock(medication_name: str):
# #     """Check stock availability"""
# #     try:
# #         result = db.check_stock(medication_name)
        
# #         if not result.get("found"):
# #             raise HTTPException(status_code=404, detail=result.get("error"))
        
# #         return {
# #             "medication": result.get("medication_name"),
# #             "in_stock": result.get("in_stock"),
# #             "quantity": result.get("quantity"),
# #             "status": result.get("status")
# #         }
    
# #     except HTTPException:
# #         raise
# #     except Exception as e:
# #         logger.error(f"Error checking stock: {e}")
# #         raise HTTPException(status_code=500, detail="Failed to check stock")

# # # ========== DEMO/TESTING ENDPOINTS ==========

# # @app.get("/demo/flows")
# # async def demo_flows():
# #     """
# #     List example conversation flows for testing
# #     """
# #     return {
# #         "flows": [
# #             {
# #                 "name": "Medication Information Flow",
# #                 "description": "Customer asks about a specific medication",
# #                 "example_messages": [
# #                     "Tell me about Acamol",
# #                     "What are the side effects?",
# #                     "Do I need a prescription?"
# #                 ]
# #             },
# #             {
# #                 "name": "Prescription Refill Flow",
# #                 "description": "Customer wants to refill their prescription",
# #                 "user_id": "user_001",
# #                 "example_messages": [
# #                     "I need to refill my prescription",
# #                     "Check if Augmentin is in stock",
# #                     "Reserve 2 boxes for me"
# #                 ]
# #             },
# #             {
# #                 "name": "Stock Check Flow",
# #                 "description": "Customer checks availability",
# #                 "example_messages": [
# #                     "Do you have Nurofen in stock?",
# #                     "How many boxes are available?",
# #                     "Can I reserve some?"
# #                 ]
# #             },
# #             {
# #                 "name": "Medical Advice Redirect",
# #                 "description": "Customer asks for medical advice (should be redirected)",
# #                 "example_messages": [
# #                     "I have a headache, what should I take?",
# #                     "Which painkiller is better for me?"
# #                 ]
# #             },
# #             {
# #                 "name": "Hebrew Conversation",
# #                 "description": "Conversation in Hebrew",
# #                 "example_messages": [
# #                     "יש לכם אקמול במלאי?",
# #                     "מה המרכיב הפעיל?",
# #                     "צריך מרשם?"
# #                 ]
# #             }
# #         ]
# #     }

# # # ========== RUN SERVER ==========

# # if __name__ == "__main__":
# #     import uvicorn
    
# #     print("=" * 70)
# #     print("🏥 PHARMACY AGENT API SERVER")
# #     print("=" * 70)
# #     print("\n📍 Server starting at: http://localhost:8000")
# #     print("📚 API Documentation: http://localhost:8000/docs")
# #     print("🔍 Health Check: http://localhost:8000/health")
# #     print("\n" + "=" * 70)
    
# #     uvicorn.run(
# #         "api:app",
# #         host="0.0.0.0",
# #         port=8000,
# #         reload=True,
# #         log_level="info"
# #     )

# """
# FastAPI Server for Pharmacy Agent - FIXED VERSION
# """

# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# from typing import List, Optional, Dict, Any
# import json
# import logging
# from agent import PharmacyAgent
# from database import db

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Initialize FastAPI app
# app = FastAPI(
#     title="Pharmacy Agent API",
#     description="AI-powered pharmacy assistant for medication information",
#     version="1.0.0"
# )

# # CORS middleware for frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, specify your frontend domain
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ========== REQUEST/RESPONSE MODELS ==========

# class Message(BaseModel):
#     role: str
#     content: str

# class ChatRequest(BaseModel):
#     message: str
#     history: Optional[List[Message]] = []
#     user_id: Optional[str] = None
#     stream: bool = True

# class ChatResponse(BaseModel):
#     response: str
#     tool_calls: Optional[List[Dict[str, Any]]] = []

# class HealthCheck(BaseModel):
#     status: str
#     database_status: str
#     tools_count: int
#     model: str

# # ========== API ENDPOINTS ==========

# @app.get("/", response_model=HealthCheck)
# async def root():
#     """Health check endpoint"""
#     return {
#         "status": "healthy",
#         "database_status": "connected",
#         "tools_count": 9,
#         "model": "gpt-4o-mini"
#     }

# @app.get("/health")
# async def health_check():
#     """Detailed health check"""
#     try:
#         # Test database
#         test_med = db.get_medication_by_name("Acamol", "en")
#         db_status = "healthy" if test_med else "degraded"
        
#         return {
#             "status": "healthy",
#             "components": {
#                 "api": "healthy",
#                 "database": db_status,
#                 "agent": "healthy"
#             },
#             "medications_count": len(db.medications.get("medications", [])),
#             "users_count": len(db.users.get("users", []))
#         }
#     except Exception as e:
#         logger.error(f"Health check failed: {e}")
#         raise HTTPException(status_code=503, detail="Service unhealthy")

# @app.get("/chat_sse")
# async def chat_sse(message: str, user_id: str = None):
#     """
#     ✅ FIXED: SSE endpoint for streaming chat
#     מקבל message כ-string ו-user_id אופציונלי
#     """
#     def event_generator():
#         """
#         Generator סינכרוני לשליחת SSE events
#         """
#         # יצירת agent חדש לכל request
#         agent = PharmacyAgent(debug=False)
        
#         try:
#             # ✅ קריאה נכונה ל-agent.chat עם user_message ו-user_id
#             for chunk in agent.chat(user_message=message, user_id=user_id, stream=True):
#                 # שליחת כל chunk כ-SSE event
#                 yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
#             # סיום - שליחת done event
#             yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
#         except Exception as e:
#             logger.error(f"Streaming error: {e}", exc_info=True)
#             # שליחת error event
#             yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

#     return StreamingResponse(
#         event_generator(), 
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "X-Accel-Buffering": "no",
#         }
#     )

# # ========== DATABASE QUERY ENDPOINTS ==========

# @app.get("/medications")
# async def list_medications(language: str = "en"):
#     """Get all medications"""
#     try:
#         medications = db.medications.get("medications", [])
        
#         formatted = []
#         for med in medications:
#             formatted.append({
#                 "id": med.get("id"),
#                 "name": med.get("name" if language == "he" else "name_en"),
#                 "active_ingredient": med.get("active_ingredient_he" if language == "he" else "active_ingredient"),
#                 "requires_prescription": med.get("requires_prescription"),
#                 "in_stock": med.get("stock_quantity", 0) > 0
#             })
        
#         return {"medications": formatted, "count": len(formatted)}
    
#     except Exception as e:
#         logger.error(f"Error listing medications: {e}")
#         raise HTTPException(status_code=500, detail="Failed to retrieve medications")

# @app.get("/medications/{medication_name}")
# async def get_medication(medication_name: str, language: str = "en"):
#     """Get specific medication details"""
#     try:
#         med = db.get_medication_by_name(medication_name, language)
        
#         if not med:
#             raise HTTPException(status_code=404, detail=f"Medication '{medication_name}' not found")
        
#         return {"medication": med}
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting medication: {e}")
#         raise HTTPException(status_code=500, detail="Failed to retrieve medication")

# @app.get("/users/{user_id}/prescriptions")
# async def get_user_prescriptions(user_id: str, language: str = "en"):
#     """Get user's prescriptions"""
#     try:
#         user = db.get_user_by_id(user_id)
#         if not user:
#             raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
        
#         prescriptions = db.get_user_prescriptions(user_id)
        
#         formatted = []
#         for med in prescriptions:
#             formatted.append({
#                 "id": med.get("id"),
#                 "name": med.get("name" if language == "he" else "name_en"),
#                 "active_ingredient": med.get("active_ingredient_he" if language == "he" else "active_ingredient"),
#                 "dosage": med.get("dosage_he" if language == "he" else "dosage")
#             })
        
#         return {
#             "user_id": user_id,
#             "user_name": user.get("name" if language == "he" else "name_en"),
#             "prescriptions": formatted,
#             "count": len(formatted)
#         }
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error getting prescriptions: {e}")
#         raise HTTPException(status_code=500, detail="Failed to retrieve prescriptions")

# @app.get("/stock/{medication_name}")
# async def check_stock(medication_name: str):
#     """Check stock availability"""
#     try:
#         result = db.check_stock(medication_name)
        
#         if not result.get("found"):
#             raise HTTPException(status_code=404, detail=result.get("error"))
        
#         return {
#             "medication": result.get("medication_name"),
#             "in_stock": result.get("in_stock"),
#             "quantity": result.get("quantity"),
#             "status": result.get("status")
#         }
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Error checking stock: {e}")
#         raise HTTPException(status_code=500, detail="Failed to check stock")

# # ========== RUN SERVER ==========

# if __name__ == "__main__":
#     import uvicorn
    
#     print("=" * 70)
#     print("🏥 PHARMACY AGENT API SERVER")
#     print("=" * 70)
#     print("\n📍 Server starting at: http://localhost:8000")
#     print("📚 API Documentation: http://localhost:8000/docs")
#     print("🔍 Health Check: http://localhost:8000/health")
#     print("\n" + "=" * 70)
    
#     uvicorn.run(
#         "api:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )

"""
FastAPI Server for Pharmacy Agent - FULLY WORKING VERSION
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import logging
from agent import PharmacyAgent
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pharmacy Agent API",
    description="AI-powered pharmacy assistant for medication information",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== REQUEST/RESPONSE MODELS ==========

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []
    user_id: Optional[str] = None
    stream: bool = True

class HealthCheck(BaseModel):
    status: str
    database_status: str
    tools_count: int
    model: str

# ========== API ENDPOINTS ==========

@app.get("/", response_model=HealthCheck)
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database_status": "connected",
        "tools_count": 9,
        "model": "gpt-5"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        test_med = db.get_medication_by_name("Acamol", "en")
        db_status = "healthy" if test_med else "degraded"
        
        return {
            "status": "healthy",
            "components": {
                "api": "healthy",
                "database": db_status,
                "agent": "healthy"
            },
            "medications_count": len(db.medications.get("medications", [])),
            "users_count": len(db.users.get("users", []))
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/ui")
async def serve_ui():
    """✅ Serve the frontend HTML"""
    return FileResponse("index.html")

@app.get("/chat_sse")
async def chat_sse(message: str, user_id: str = None):
    """
    ✅ FIXED: SSE endpoint with correct parameters
    """
    logger.info(f"Received SSE request: message={message[:50]}..., user_id={user_id}")
    
    def event_generator():
        """Simple synchronous generator for SSE"""
        try:
            # ✅ Build messages list correctly
            messages = []
            
            if user_id:
                messages.append({
                    "role": "system",
                    "content": f"Customer ID: {user_id}. Fetch prescriptions and relevant info for this user."
                })
            
            messages.append({"role": "user", "content": message})
            
            # ✅ Create agent and call with correct parameters
            agent = PharmacyAgent(debug=False)
            
            logger.info(f"Starting agent.chat with {len(messages)} messages")
            
            # ✅ Call agent.chat with messages (not user_message!)
            for chunk in agent.chat(messages=messages, stream=True):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            
            # Send done event
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
            logger.info("Stream completed successfully")
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

# ========== DATABASE QUERY ENDPOINTS ==========

@app.get("/medications")
async def list_medications(language: str = "en"):
    """Get all medications"""
    try:
        medications = db.medications.get("medications", [])
        
        formatted = []
        for med in medications:
            formatted.append({
                "id": med.get("id"),
                "name": med.get("name" if language == "he" else "name_en"),
                "active_ingredient": med.get("active_ingredient_he" if language == "he" else "active_ingredient"),
                "requires_prescription": med.get("requires_prescription"),
                "in_stock": med.get("stock_quantity", 0) > 0
            })
        
        return {"medications": formatted, "count": len(formatted)}
    
    except Exception as e:
        logger.error(f"Error listing medications: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve medications")

@app.get("/medications/{medication_name}")
async def get_medication(medication_name: str, language: str = "en"):
    """Get specific medication details"""
    try:
        med = db.get_medication_by_name(medication_name, language)
        
        if not med:
            raise HTTPException(status_code=404, detail=f"Medication '{medication_name}' not found")
        
        return {"medication": med}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medication: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve medication")

@app.get("/users/{user_id}/prescriptions")
async def get_user_prescriptions(user_id: str, language: str = "en"):
    """Get user's prescriptions"""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
        
        prescriptions = db.get_user_prescriptions(user_id)
        
        formatted = []
        for med in prescriptions:
            formatted.append({
                "id": med.get("id"),
                "name": med.get("name" if language == "he" else "name_en"),
                "active_ingredient": med.get("active_ingredient_he" if language == "he" else "active_ingredient"),
                "dosage": med.get("dosage_he" if language == "he" else "dosage")
            })
        
        return {
            "user_id": user_id,
            "user_name": user.get("name" if language == "he" else "name_en"),
            "prescriptions": formatted,
            "count": len(formatted)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prescriptions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve prescriptions")

@app.get("/stock/{medication_name}")
async def check_stock(medication_name: str):
    """Check stock availability"""
    try:
        result = db.check_stock(medication_name)
        
        if not result.get("found"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        
        return {
            "medication": result.get("medication_name"),
            "in_stock": result.get("in_stock"),
            "quantity": result.get("quantity"),
            "status": result.get("status")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking stock: {e}")
        raise HTTPException(status_code=500, detail="Failed to check stock")

# ========== RUN SERVER ==========

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("🏥 PHARMACY AGENT API SERVER")
    print("=" * 70)
    print("\n📍 API Server: http://localhost:8000")
    print("🌐 Frontend UI: http://localhost:8000/ui")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/health")
    print("💬 Test SSE: http://localhost:8000/chat_sse?message=Tell%20me%20about%20Acamol")
    print("\n" + "=" * 70)
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )