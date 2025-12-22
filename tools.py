"""
Tools/Functions for the OpenAI Agent
These are the functions the Agent can call to interact with the pharmacy database.
"""

from typing import Dict, Any, List
from database import db
import json


# ========== TOOL DEFINITIONS (OpenAI Function Calling Schema) ==========

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_medication_info",
            "description": "When user asks general information about a medication (what it is, usage, dosage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "medication_name": {
                        "type": "string",
                        "description": "Name of the medication in Hebrew or English (e.g., 'אקמול', 'Acamol', 'נורופן', 'Nurofen')"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "he"],
                        "description": "Preferred language for the response. Use 'he' for Hebrew, 'en' for English. Default is 'en'."
                    }
                },
                "required": ["medication_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock_availability",
            "description": "When user asks if a medication is in stock or available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medication_name": {
                        "type": "string",
                        "description": "Name of the medication to check (Hebrew or English)"
                    }
                },
                "required": ["medication_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_prescription_requirement",
            "description": "When user asks if a medication requires a prescription or is over-the-counter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medication_name": {
                        "type": "string",
                        "description": "Name of the medication (Hebrew or English)"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "he"],
                        "description": "Preferred language for the response"
                    }
                },
                "required": ["medication_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_active_ingredient",
            "description": "When user asks for medications containing a specific active ingredient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient": {
                        "type": "string",
                        "description": "The active ingredient to search for (e.g., 'Paracetamol', 'Ibuprofen', 'פרצטמול')"
                    }
                },
                "required": ["ingredient"],
                "additionalProperties": False
            }
        }
    },
    # ===== PRESCRIPTION MANAGEMENT =====
    {
        "type": "function",
        "function": {
            "name": "get_user_prescriptions",
            "description": "When user asks about their prescriptions (e.g. 'my prescriptions', 'המרשמים שלי').",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID (e.g., 'user_001')"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "he"],
                        "description": "Preferred language for the response"
                    }
                },
                "required": ["user_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_prescription_eligibility",
            "description": "When user asks if they have a prescription for a specific medication.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID"
                    },
                    "medication_name": {
                        "type": "string",
                        "description": "Name of the medication to verify"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "he"],
                        "description": "Preferred language for the response"
                    }
                },
                "required": ["user_id", "medication_name"],
                "additionalProperties": False
            }
        }
    },
    # ===== INVENTORY CONTROL =====
    {
        "type": "function",
        "function": {
            "name": "reserve_medication",
            "description": "When user asks to reserve medication for pickup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medication_name": {
                        "type": "string",
                        "description": "Name of medication to reserve"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of units to reserve",
                        "minimum": 1
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID making the reservation"
                    }
                },
                "required": ["medication_name", "quantity", "user_id"],
                "additionalProperties": False
            }
        }
    },
    # ===== CUSTOMER SERVICE =====
    {
        "type": "function",
        "function": {
            "name": "check_drug_interactions",
            "description": "When user asks if medications are safe to take together.",
            "parameters": {
                "type": "object",
                "properties": {
                    "medications": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of medication names to check for interactions (minimum 2)",
                        "minItems": 2
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "he"],
                        "description": "Preferred language for the response"
                    }
                },
                "required": ["medications"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_user_allergies",
            "description": "When user asks if a medication is safe due to allergy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID"
                    },
                    "medication_name": {
                        "type": "string",
                        "description": "Medication name to check against user allergies"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "he"],
                        "description": "Preferred language for the response"
                    }
                },
                "required": ["user_id", "medication_name"],
                "additionalProperties": False
            }
        }
    }
]


# ========== TOOL EXECUTION FUNCTIONS ==========

def execute_get_medication_info(medication_name: str, language: str = "en") -> Dict[str, Any]:
    """
    Execute: Get detailed medication information
    
    Args:
        medication_name: Name of medication
        language: Response language ('en' or 'he')
    
    Returns:
        Dict with medication details or error
    """
    # Input validation
    if not medication_name or not medication_name.strip():
        return {
            "success": False,
            "error": "Medication name is required" if language == "en" else "שם התרופה נדרש"
        }
    
    # Query database
    result = db.get_medication_by_name(medication_name.strip(), language)
    
    # Handle not found
    if not result:
        return {
            "success": False,
            "error": f"Medication '{medication_name}' not found in our database" if language == "en" 
                    else f"התרופה '{medication_name}' לא נמצאה במאגר שלנו"
        }
    
    # Success response
    return {
        "success": True,
        "medication": result
    }


def execute_check_stock_availability(medication_name: str) -> Dict[str, Any]:
    """
    Execute: Check stock availability
    
    Args:
        medication_name: Name of medication
    
    Returns:
        Dict with stock status
    """
    if not medication_name or not medication_name.strip():
        return {
            "success": False,
            "error": "Medication name is required"
        }
    
    result = db.check_stock(medication_name.strip())
    
    if not result.get("found"):
        return {
            "success": False,
            "error": result.get("error", "Medication not found")
        }
    
    return {
        "success": True,
        "medication_name": result.get("medication_name"),
        "in_stock": result.get("in_stock"),
        "quantity": result.get("quantity"),
        "status": result.get("status")
    }


def execute_check_prescription_requirement(medication_name: str, language: str = "en") -> Dict[str, Any]:
    """
    Execute: Check prescription requirement
    
    Args:
        medication_name: Name of medication
        language: Response language
    
    Returns:
        Dict with prescription info
    """
    if not medication_name or not medication_name.strip():
        return {
            "success": False,
            "error": "Medication name is required" if language == "en" else "שם התרופה נדרש"
        }
    
    result = db.check_prescription_requirement(medication_name.strip(), language)
    
    if not result.get("found"):
        return {
            "success": False,
            "error": result.get("error", "Medication not found")
        }
    
    return {
        "success": True,
        "medication_name": result.get("medication_name"),
        "requires_prescription": result.get("requires_prescription"),
        "message": result.get("message")
    }


def execute_search_by_active_ingredient(ingredient: str) -> Dict[str, Any]:
    """
    Execute: Search medications by active ingredient
    
    Args:
        ingredient: Active ingredient to search for
    
    Returns:
        Dict with list of medications
    """
    if not ingredient or not ingredient.strip():
        return {
            "success": False,
            "error": "Ingredient name is required"
        }
    
    results = db.search_medications_by_ingredient(ingredient.strip())
    
    return {
        "success": True,
        "ingredient": ingredient,
        "count": len(results),
        "medications": results
    }


# ========== PRESCRIPTION MANAGEMENT ==========

def execute_get_user_prescriptions(user_id: str, language: str = "en") -> Dict[str, Any]:
    """
    Execute: Get user's active prescriptions
    
    Args:
        user_id: User ID
        language: Response language
    
    Returns:
        Dict with user's prescription medications
    """
    if not user_id or not user_id.strip():
        return {
            "success": False,
            "error": "User ID is required" if language == "en" else "מזהה משתמש נדרש"
        }
    
    user = db.get_user_by_id(user_id.strip())
    if not user:
        return {
            "success": False,
            "error": f"User '{user_id}' not found" if language == "en" else f"משתמש '{user_id}' לא נמצא"
        }
    
    prescriptions = db.get_user_prescriptions(user_id.strip())
    
    # Format prescriptions based on language
    formatted_prescriptions = []
    for med in prescriptions:
        formatted_prescriptions.append({
            "name": med.get("name" if language == "he" else "name_en"),
            "active_ingredient": med.get("active_ingredient_he" if language == "he" else "active_ingredient"),
            "dosage": med.get("dosage_he" if language == "he" else "dosage"),
            "id": med.get("id")
        })
    
    return {
        "success": True,
        "user_id": user_id,
        "user_name": user.get("name" if language == "he" else "name_en"),
        "prescription_count": len(formatted_prescriptions),
        "prescriptions": formatted_prescriptions
    }


def execute_verify_prescription_eligibility(user_id: str, medication_name: str, language: str = "en") -> Dict[str, Any]:
    """
    Execute: Verify if user has valid prescription for medication
    
    Args:
        user_id: User ID
        medication_name: Medication to verify
        language: Response language
    
    Returns:
        Dict with verification result
    """
    if not user_id or not medication_name:
        return {
            "success": False,
            "error": "User ID and medication name are required" if language == "en" 
                    else "מזהה משתמש ושם תרופה נדרשים"
        }
    
    # Get user
    user = db.get_user_by_id(user_id.strip())
    if not user:
        return {
            "success": False,
            "error": f"User not found" if language == "en" else "משתמש לא נמצא"
        }
    
    # Get medication
    med = db.get_medication_by_name(medication_name.strip(), language)
    if not med:
        return {
            "success": False,
            "error": f"Medication '{medication_name}' not found" if language == "en"
                    else f"התרופה '{medication_name}' לא נמצאה"
        }
    
    # Check if prescription required
    if not med.get("requires_prescription"):
        return {
            "success": True,
            "requires_prescription": False,
            "eligible": True,
            "message": "This medication does not require a prescription" if language == "en"
                      else "תרופה זו אינה דורשת מרשם"
        }
    
    # Check if user has prescription
    user_prescriptions = db.get_user_prescriptions(user_id)
    has_prescription = any(p.get("id") == med.get("id") for p in user_prescriptions)
    
    return {
        "success": True,
        "requires_prescription": True,
        "eligible": has_prescription,
        "medication_name": med.get("name"),
        "message": ("Valid prescription found" if has_prescription else "Prescription required - please consult your doctor")
                   if language == "en" else 
                   ("מרשם תקף נמצא" if has_prescription else "נדרש מרשם - אנא פנה לרופא")
    }


# ========== INVENTORY CONTROL ==========

def execute_reserve_medication(medication_name: str, quantity: int, user_id: str) -> Dict[str, Any]:
    """
    Execute: Reserve medication for pickup (simulated)
    
    Args:
        medication_name: Medication to reserve
        quantity: Number of units
        user_id: User making reservation
    
    Returns:
        Dict with reservation confirmation
    """
    if not medication_name or not user_id:
        return {
            "success": False,
            "error": "Medication name and user ID are required"
        }
    
    if quantity < 1:
        return {
            "success": False,
            "error": "Quantity must be at least 1"
        }
    
    # Check stock
    stock_result = db.check_stock(medication_name.strip())
    if not stock_result.get("found"):
        return {
            "success": False,
            "error": f"Medication '{medication_name}' not found"
        }
    
    available_quantity = stock_result.get("quantity", 0)
    
    if available_quantity < quantity:
        return {
            "success": False,
            "error": f"Insufficient stock. Requested: {quantity}, Available: {available_quantity}",
            "available_quantity": available_quantity
        }
    
    # Simulate reservation (in real system, this would update database)
    import random
    reservation_id = f"RES-{random.randint(10000, 99999)}"
    
    return {
        "success": True,
        "reservation_id": reservation_id,
        "medication_name": stock_result.get("medication_name"),
        "quantity": quantity,
        "user_id": user_id,
        "message": f"Reservation confirmed. Please pick up within 48 hours. Reservation ID: {reservation_id}"
    }


# ========== CUSTOMER SERVICE ==========

def execute_check_drug_interactions(medications: List[str], language: str = "en") -> Dict[str, Any]:
    """
    Execute: Check for drug interactions (simulated with basic rules)
    
    Args:
        medications: List of medication names
        language: Response language
    
    Returns:
        Dict with interaction warnings
    """
    if not medications or len(medications) < 2:
        return {
            "success": False,
            "error": "At least 2 medications required" if language == "en" 
                    else "נדרשות לפחות 2 תרופות"
        }
    
    # Get medication details
    med_objects = []
    for med_name in medications:
        med = db.get_medication_by_name(med_name.strip(), language)
        if med:
            med_objects.append(med)
    
    if len(med_objects) < 2:
        return {
            "success": False,
            "error": "Could not find all medications in database"
        }
    
    # Simulated interaction detection (basic rules)
    interactions = []
    
    # Check for NSAIDs together (Ibuprofen + others)
    ingredients = [m.get("active_ingredient", "").lower() for m in med_objects]
    if "ibuprofen" in ingredients and any(x in ingredients for x in ["paracetamol", "metamizole"]):
        interactions.append({
            "severity": "moderate",
            "warning": "Combining NSAIDs may increase stomach irritation risk. Take with food." 
                      if language == "en" else "שילוב משככי כאבים עלול להגביר גירוי קיבה. יש ליטול עם אוכל."
        })
    
    return {
        "success": True,
        "medications_checked": [m.get("name") for m in med_objects],
        "interaction_count": len(interactions),
        "interactions": interactions,
        "message": ("No significant interactions detected" if len(interactions) == 0 
                   else f"Found {len(interactions)} potential interaction(s)")
                   if language == "en" else
                   ("לא נמצאו אינטראקציות משמעותיות" if len(interactions) == 0
                   else f"נמצאו {len(interactions)} אינטראקציות אפשריות")
    }


def execute_check_user_allergies(user_id: str, medication_name: str, language: str = "en") -> Dict[str, Any]:
    """
    Execute: Check if user is allergic to medication
    
    Args:
        user_id: User ID
        medication_name: Medication to check
        language: Response language
    
    Returns:
        Dict with allergy check result
    """
    if not user_id or not medication_name:
        return {
            "success": False,
            "error": "User ID and medication name are required" if language == "en"
                    else "מזהה משתמש ושם תרופה נדרשים"
        }
    
    # Get user
    user = db.get_user_by_id(user_id.strip())
    if not user:
        return {
            "success": False,
            "error": "User not found" if language == "en" else "משתמש לא נמצא"
        }
    
    # Get medication
    med = db.get_medication_by_name(medication_name.strip(), language)
    if not med:
        return {
            "success": False,
            "error": f"Medication not found" if language == "en" else "תרופה לא נמצאה"
        }
    
    # Check allergies
    user_allergies = [a.lower() for a in user.get("allergies", [])]
    med_ingredient = med.get("active_ingredient", "").lower()
    med_name = med.get("name", "").lower()
    
    has_allergy = (med_ingredient in user_allergies or 
                   med_name in user_allergies or
                   any(allergy in med_ingredient for allergy in user_allergies))
    
    if has_allergy:
        matching_allergies = [a for a in user.get("allergies", []) 
                             if a.lower() in med_ingredient or a.lower() in med_name]
        return {
            "success": True,
            "has_allergy": True,
            "safe_to_use": False,
            "allergies": matching_allergies,
            "message": f"⚠️ ALLERGY WARNING: User is allergic to {', '.join(matching_allergies)}" 
                      if language == "en" else 
                      f"⚠️ אזהרת אלרגיה: המשתמש אלרגי ל-{', '.join(matching_allergies)}"
        }
    
    return {
        "success": True,
        "has_allergy": False,
        "safe_to_use": True,
        "message": "No known allergies to this medication" if language == "en"
                  else "אין אלרגיות ידועות לתרופה זו"
    }


# ========== TOOL DISPATCHER ==========

import time
import json
from typing import Dict, Any

# פשוט dict memory cache
TOOL_CACHE = {}

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Main dispatcher - routes tool calls to appropriate functions with timing and cache
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Arguments passed by the Agent
    
    Returns:
        JSON string with execution result
    """
    global TOOL_CACHE
    start = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] execute_tool START: {tool_name}, args={arguments}")

    # Build cache key
    cache_key = f"{tool_name}-{json.dumps(arguments, sort_keys=True)}"
    if cache_key in TOOL_CACHE:
        result = TOOL_CACHE[cache_key]
        print(f"[{time.strftime('%H:%M:%S')}] execute_tool CACHE HIT: {tool_name}")
        end = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] execute_tool END (cached) {tool_name}: {end - start:.2f}s")
        return result

    # Map tool names to execution functions
    tool_map = {
        "get_medication_info": execute_get_medication_info,
        "check_stock_availability": execute_check_stock_availability,
        "check_prescription_requirement": execute_check_prescription_requirement,
        "search_by_active_ingredient": execute_search_by_active_ingredient,
        "get_user_prescriptions": execute_get_user_prescriptions,
        "verify_prescription_eligibility": execute_verify_prescription_eligibility,
        "reserve_medication": execute_reserve_medication,
        "check_drug_interactions": execute_check_drug_interactions,
        "check_user_allergies": execute_check_user_allergies
    }

    if tool_name not in tool_map:
        result = json.dumps({
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }, ensure_ascii=False)
        print(f"[{time.strftime('%H:%M:%S')}] execute_tool END (unknown tool): {tool_name}")
        return result

    try:
        # Measure DB/query time inside the tool if needed
        db_start = time.time()
        tool_result = tool_map[tool_name](**arguments)
        db_end = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] Tool DB/processing time: {db_end - db_start:.2f}s")

        result = json.dumps(tool_result, ensure_ascii=False, indent=2)

        # Save to cache
        TOOL_CACHE[cache_key] = result

        end = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] execute_tool END: {tool_name}, total {end - start:.2f}s")
        return result

    except TypeError as e:
        result = json.dumps({
            "success": False,
            "error": f"Invalid arguments for {tool_name}: {str(e)}"
        }, ensure_ascii=False)
        print(f"[{time.strftime('%H:%M:%S')}] execute_tool END (TypeError): {tool_name}")
        return result

    except Exception as e:
        result = json.dumps({
            "success": False,
            "error": f"Error executing {tool_name}: {str(e)}"
        }, ensure_ascii=False)
        print(f"[{time.strftime('%H:%M:%S')}] execute_tool END (Exception): {tool_name}")
        return result



# ========== TESTING ==========

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING PHARMACY AGENT TOOLS")
    print("=" * 60)
    
    # Test 1: Get medication info (Hebrew)
    print("\n📋 Test 1: Get medication info (Hebrew)")
    result = execute_tool("get_medication_info", {
        "medication_name": "אקמול",
        "language": "he"
    })
    print(result)
    
    # Test 2: Check stock
    print("\n📦 Test 2: Check stock availability")
    result = execute_tool("check_stock_availability", {
        "medication_name": "Nurofen"
    })
    print(result)
    
    # Test 3: Check prescription requirement
    print("\n💊 Test 3: Check prescription requirement")
    result = execute_tool("check_prescription_requirement", {
        "medication_name": "augmentin",
        "language": "en"
    })
    print(result)
    
    # Test 4: Search by ingredient
    print("\n🔍 Test 4: Search by active ingredient")
    result = execute_tool("search_by_active_ingredient", {
        "ingredient": "Paracetamol"
    })
    print(result)
    
    # Test 5: Get user prescriptions
    print("\n📝 Test 5: Get user prescriptions (Prescription Management)")
    result = execute_tool("get_user_prescriptions", {
        "user_id": "user_001",
        "language": "en"
    })
    print(result)
    
    # Test 6: Verify prescription eligibility
    print("\n✅ Test 6: Verify prescription eligibility")
    result = execute_tool("verify_prescription_eligibility", {
        "user_id": "user_001",
        "medication_name": "Augmentin",
        "language": "en"
    })
    print(result)
    
    # Test 7: Reserve medication (Inventory Control)
    print("\n🏪 Test 7: Reserve medication")
    result = execute_tool("reserve_medication", {
        "medication_name": "Acamol",
        "quantity": 2,
        "user_id": "user_003"
    })
    print(result)
    
    # Test 8: Check drug interactions (Customer Service)
    print("\n⚠️ Test 8: Check drug interactions")
    result = execute_tool("check_drug_interactions", {
        "medications": ["Nurofen", "Acamol"],
        "language": "en"
    })
    print(result)
    
    # Test 9: Check user allergies (Customer Service)
    print("\n🚨 Test 9: Check user allergies")
    result = execute_tool("check_user_allergies", {
        "user_id": "user_002",
        "medication_name": "Nurofen",
        "language": "en"
    })
    print(result)
    
    # Test 10: Error handling - medication not found
    print("\n❌ Test 10: Error handling")
    result = execute_tool("get_medication_info", {
        "medication_name": "NonExistentMed",
        "language": "en"
    })
    print(result)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print("\nTool Categories:")
    print("  📋 Basic Info: 4 tools")
    print("  💊 Prescription Management: 2 tools")
    print("  📦 Inventory Control: 1 tool")
    print("  🏥 Customer Service: 2 tools")
    print("  ━━━━━━━━━━━━━━━━━━━━━━")
    print("  TOTAL: 9 tools")