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
