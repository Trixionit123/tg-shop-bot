from typing import Dict, List, Optional
from loyalty_system import LoyaltySystem

class OrderSystem:
    def __init__(self):
        self.loyalty_system = LoyaltySystem()
        self.products = {
            "Блок 20w (AAA+)": 1500,
            "Кабель lightning": 800,
            "Кабель Magsafe": 1200
        }
        self.delivery_methods = {
            1: "Самовывоз",
            2: "Курьер",
            3: "Почта России"
        }

    def get_products(self) -> Dict[str, float]:
        """Return available products and their prices"""
        return self.products

    def get_delivery_methods(self) -> Dict[int, str]:
        """Return available delivery methods"""
        return self.delivery_methods

    def calculate_total(self, product: str, quantity: int, use_points: bool, user_id: str) -> Dict:
        """Calculate total price with potential loyalty points discount"""
        if product not in self.products:
            raise ValueError("Invalid product selected")

        base_price = self.products[product] * quantity
        points_discount = 0
        points_used = 0
        
        if use_points:
            user_loyalty = self.loyalty_system.get_user_loyalty(user_id)
            available_points = user_loyalty["points"]
            # Convert points to money (1 point = 1 ruble)
            max_possible_discount = min(available_points, base_price)
            
            if max_possible_discount > 0:
                points_used = max_possible_discount
                points_discount = max_possible_discount
                self.loyalty_system.use_points(user_id, points_used)

        final_price = base_price - points_discount
        
        # Calculate new points earned
        if final_price > 0:
            result = self.loyalty_system.update_user_loyalty(user_id, final_price)
            points_earned = result["points_earned"]
        else:
            points_earned = 0

        return {
            "product": product,
            "quantity": quantity,
            "base_price": base_price,
            "points_discount": points_discount,
            "points_used": points_used,
            "points_earned": points_earned,
            "final_price": final_price
        } 