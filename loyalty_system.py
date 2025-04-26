import json
from typing import Dict, Any
from decimal import Decimal

class LoyaltySystem:
    def __init__(self, loyalty_file: str = 'loyalty.json'):
        self.loyalty_file = loyalty_file
        self.loyalty_data = self._load_loyalty_data()

    def _load_loyalty_data(self) -> Dict[str, Dict[str, float]]:
        try:
            with open(self.loyalty_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _save_loyalty_data(self):
        with open(self.loyalty_file, 'w', encoding='utf-8') as f:
            json.dump(self.loyalty_data, f, indent=2)

    def calculate_points_for_order(self, order_amount: float) -> int:
        """Calculate loyalty points for an order based on the amount spent."""
        # Basic rule: 1 point for every 20 spent
        points = int(order_amount // 20)
        return points

    def update_user_loyalty(self, user_id: str, order_amount: float) -> Dict[str, Any]:
        """Update user's loyalty points and total spent amount."""
        if user_id not in self.loyalty_data:
            self.loyalty_data[user_id] = {
                "points": 0,
                "total_spent": 0
            }

        points_earned = self.calculate_points_for_order(order_amount)
        self.loyalty_data[user_id]["points"] += points_earned
        self.loyalty_data[user_id]["total_spent"] += order_amount
        
        self._save_loyalty_data()
        
        return {
            "user_id": user_id,
            "points_earned": points_earned,
            "total_points": self.loyalty_data[user_id]["points"],
            "total_spent": self.loyalty_data[user_id]["total_spent"]
        }

    def get_user_loyalty(self, user_id: str) -> Dict[str, Any]:
        """Get user's current loyalty status."""
        if user_id not in self.loyalty_data:
            return {
                "user_id": user_id,
                "points": 0,
                "total_spent": 0
            }
        
        return {
            "user_id": user_id,
            "points": self.loyalty_data[user_id]["points"],
            "total_spent": self.loyalty_data[user_id]["total_spent"]
        }

    def use_points(self, user_id: str, points_to_use: int) -> bool:
        """Use loyalty points for a discount. Returns True if successful."""
        if user_id not in self.loyalty_data:
            return False
            
        if self.loyalty_data[user_id]["points"] < points_to_use:
            return False
            
        self.loyalty_data[user_id]["points"] -= points_to_use
        self._save_loyalty_data()
        return True

# Example usage:
if __name__ == "__main__":
    loyalty = LoyaltySystem()
    
    # Example: Process a new order
    user_id = "7100115774"
    order_amount = 100.0
    
    result = loyalty.update_user_loyalty(user_id, order_amount)
    print(f"Updated loyalty for user {user_id}:")
    print(f"Points earned: {result['points_earned']}")
    print(f"Total points: {result['total_points']}")
    print(f"Total spent: {result['total_spent']}") 