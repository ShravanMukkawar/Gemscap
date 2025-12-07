"""
Alert Manager - Handles custom alerts and notifications
"""
import uuid
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages alert rules and triggers"""
    
    def __init__(self):
        self.rules: Dict[str, Dict] = {}
        self.triggered_alerts: List[Dict] = []
        self.max_triggered_history = 1000
    
    def add_rule(self, name: str, condition: str, symbols: List[str], enabled: bool = True) -> str:
        """Add a new alert rule"""
        rule_id = str(uuid.uuid4())
        
        self.rules[rule_id] = {
            "id": rule_id,
            "name": name,
            "condition": condition,
            "symbols": symbols,
            "enabled": enabled,
            "created_at": datetime.utcnow().isoformat(),
            "trigger_count": 0
        }
        
        logger.info(f"Added alert rule: {name}")
        return rule_id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False
    
    def get_all_rules(self) -> List[Dict]:
        """Get all alert rules"""
        return list(self.rules.values())
    
    async def check_tick(self, tick: Dict):
        """Check if any alert should trigger"""
        symbol = tick['symbol']
        price = tick['price']
        
        for rule_id, rule in self.rules.items():
            if not rule["enabled"]:
                continue
            
            if symbol not in rule["symbols"]:
                continue
            
            try:
                if self._evaluate_condition(rule["condition"], tick):
                    self._trigger_alert(rule, tick)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule_id}: {e}")
    
    def _evaluate_condition(self, condition: str, tick: Dict) -> bool:
        """Evaluate an alert condition"""
        try:
            context = {
                "price": tick["price"],
                "size": tick["size"],
            }
            
            parts = condition.strip().split()
            if len(parts) != 3:
                return False
            
            variable, operator, threshold = parts
            threshold = float(threshold)
            
            if variable not in context:
                return False
            
            value = context[variable]
            
            if operator == ">":
                return value > threshold
            elif operator == "<":
                return value < threshold
            elif operator == ">=":
                return value >= threshold
            elif operator == "<=":
                return value <= threshold
            elif operator == "==":
                return abs(value - threshold) < 1e-6
            
        except Exception as e:
            logger.error(f"Error parsing condition '{condition}': {e}")
            return False
        
        return False
    
    def _trigger_alert(self, rule: Dict, tick: Dict):
        """Trigger an alert"""
        alert = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "symbol": tick["symbol"],
            "price": tick["price"],
            "timestamp": tick["ts"],
            "triggered_at": datetime.utcnow().isoformat(),
            "condition": rule["condition"]
        }
        
        self.triggered_alerts.insert(0, alert)
        
        if len(self.triggered_alerts) > self.max_triggered_history:
            self.triggered_alerts = self.triggered_alerts[:self.max_triggered_history]
        
        rule["trigger_count"] += 1
        
        logger.info(f"Alert triggered: {rule['name']} for {tick['symbol']} @ {tick['price']}")
    
    def get_triggered_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recently triggered alerts"""
        return self.triggered_alerts[:limit]