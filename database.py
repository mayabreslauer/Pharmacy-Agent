import json
from pathlib import Path
from typing import Optional, List, Dict, Any

class PharmacyDatabase:
    """Simple JSON-based database for pharmacy data"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(__file__).parent / data_dir
        self.medications = self._load_json("medications.json")
        self.users = self._load_json("users.json")
    
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON file"""
        file_path = self.data_dir / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found at {file_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error decoding {filename}: {e}")
            return {}
    
    # ========== MEDICATION QUERIES ==========
    
    def get_medication_by_name(self, name: str, language: str = "en") -> Optional[Dict[str, Any]]:
        """
        Get medication information by name (case-insensitive, supports Hebrew and English)
        
        Args:
            name: Medication name in Hebrew or English
            language: Preferred response language ('en' or 'he')
            
        Returns:
            Medication dict or None if not found
        """
        name_lower = name.lower().strip()
        
        for med in self.medications.get("medications", []):
            # Check both Hebrew and English names
            if (med.get("name", "").lower() == name_lower or 
                med.get("name_en", "").lower() == name_lower):
                return self._format_medication(med, language)
        
        return None
    
    def check_stock(self, medication_name: str) -> Dict[str, Any]:
        """
        Check stock availability for a medication
        
        Returns:
            Dict with availability status and quantity
        """
        med = self.get_medication_by_name(medication_name, language="en")
        
        if not med:
            return {
                "found": False,
                "error": f"Medication '{medication_name}' not found in database"
            }
        
        quantity = med.get("stock_quantity", 0)
        
        return {
            "found": True,
            "medication_name": med.get("name_en"),
            "in_stock": quantity > 0,
            "quantity": quantity,
            "status": "available" if quantity > 10 else "low_stock" if quantity > 0 else "out_of_stock"
        }
    
    def check_prescription_requirement(self, medication_name: str, language: str = "en") -> Dict[str, Any]:
        """
        Check if medication requires prescription
        
        Returns:
            Dict with prescription requirement info
        """
        med = self.get_medication_by_name(medication_name, language)
        
        if not med:
            return {
                "found": False,
                "error": f"Medication '{medication_name}' not found in database"
            }
        
        requires_rx = med.get("requires_prescription", False)
        
        response = {
            "found": True,
            "medication_name": med.get("name" if language == "he" else "name_en"),
            "requires_prescription": requires_rx
        }
        
        if language == "he":
            response["message"] = f"{'דורש' if requires_rx else 'לא דורש'} מרשם רופא"
        else:
            response["message"] = f"{'Requires' if requires_rx else 'Does not require'} prescription"
        
        return response
    
    def search_medications_by_ingredient(self, ingredient: str) -> List[Dict[str, Any]]:
        """
        Search medications by active ingredient
        
        Returns:
            List of medications containing the ingredient
        """
        ingredient_lower = ingredient.lower()
        results = []
        
        for med in self.medications.get("medications", []):
            active_ing = med.get("active_ingredient", "").lower()
            active_ing_he = med.get("active_ingredient_he", "").lower()
            
            if ingredient_lower in active_ing or ingredient_lower in active_ing_he:
                results.append(self._format_medication(med, "en"))
        
        return results
    
    def _format_medication(self, med: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """Format medication data based on language preference"""
        if language == "he":
            return {
                "id": med.get("id"),
                "name": med.get("name"),
                "active_ingredient": med.get("active_ingredient_he"),
                "dosage": med.get("dosage_he"),
                "usage": med.get("usage_he"),
                "requires_prescription": med.get("requires_prescription"),
                "stock_quantity": med.get("stock_quantity"),
                "price": med.get("price"),
                "warnings": med.get("warnings_he")
            }
        else:
            return {
                "id": med.get("id"),
                "name": med.get("name_en"),
                "active_ingredient": med.get("active_ingredient"),
                "dosage": med.get("dosage"),
                "usage": med.get("usage"),
                "requires_prescription": med.get("requires_prescription"),
                "stock_quantity": med.get("stock_quantity"),
                "price": med.get("price"),
                "warnings": med.get("warnings")
            }
    
    # ========== USER QUERIES (Optional for this assignment) ==========
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by ID"""
        for user in self.users.get("users", []):
            if user.get("id") == user_id:
                return user
        return None
    
    def get_user_prescriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all prescriptions for a user"""
        user = self.get_user_by_id(user_id)
        if not user:
            return []
        
        prescription_ids = user.get("prescriptions", [])
        prescriptions = []
        
        for med_id in prescription_ids:
            for med in self.medications.get("medications", []):
                if med.get("id") == med_id:
                    prescriptions.append(med)
        
        return prescriptions


# Create singleton instance
db = PharmacyDatabase()


# ========== TESTING ==========
if __name__ == "__main__":
    print("Testing Pharmacy Database...")
    print("\n1. Get medication by name (Hebrew):")
    result = db.get_medication_by_name("אקמול", language="he")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n2. Check stock:")
    result = db.check_stock("Acamol")
    print(json.dumps(result, indent=2))
    
    print("\n3. Check prescription requirement:")
    result = db.check_prescription_requirement("augmentin", language="en")
    print(json.dumps(result, indent=2))
    
    print("\n4. Search by ingredient:")
    results = db.search_medications_by_ingredient("paracetamol")
    print(f"Found {len(results)} medications")