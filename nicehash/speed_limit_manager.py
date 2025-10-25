#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Speed Limit Manager
Manages maximum speed limits for NiceHash orders
"""

import logging
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SpeedLimitMode(Enum):
    """Speed limit modes"""
    FIXED = "fixed"          # Fixed speed limit
    ADAPTIVE = "adaptive"    # Adaptive based on market conditions
    DYNAMIC = "dynamic"      # Dynamic based on profitability

@dataclass
class SpeedLimitConfig:
    """Speed limit configuration"""
    max_speed_limit: float = 1000.0  # Maximum speed in TH/s
    mode: SpeedLimitMode = SpeedLimitMode.ADAPTIVE
    adaptive_factor: float = 0.8  # Factor for adaptive mode (0.8 = 80% of max)
    dynamic_threshold: float = 0.01  # Profit threshold for dynamic mode
    min_speed_limit: float = 100.0  # Minimum speed limit
    speed_increment: float = 50.0   # Speed increment steps

class SpeedLimitManager:
    """Speed limit manager for NiceHash orders"""
    
    def __init__(self, config: SpeedLimitConfig):
        self.config = config
        self.current_speed_limit = config.max_speed_limit
        self.speed_history = []  # Track speed changes
        self.market_conditions = {}  # Store market condition data
    
    def get_current_speed_limit(self) -> float:
        """Get current speed limit"""
        return self.current_speed_limit
    
    def calculate_optimal_speed(self, algorithm: str, profit: float, market_volatility: float = 0.0) -> float:
        """Calculate optimal speed based on current conditions"""
        if self.config.mode == SpeedLimitMode.FIXED:
            return self.config.max_speed_limit
        
        elif self.config.mode == SpeedLimitMode.ADAPTIVE:
            return self._calculate_adaptive_speed(profit, market_volatility)
        
        elif self.config.mode == SpeedLimitMode.DYNAMIC:
            return self._calculate_dynamic_speed(algorithm, profit)
        
        return self.config.max_speed_limit
    
    def _calculate_adaptive_speed(self, profit: float, market_volatility: float) -> float:
        """Calculate adaptive speed based on profit and volatility"""
        base_speed = self.config.max_speed_limit * self.config.adaptive_factor
        
        # Adjust based on profit
        profit_factor = min(profit / 0.01, 2.0)  # Cap at 2x for high profit
        
        # Adjust based on volatility (lower volatility = higher speed)
        volatility_factor = max(0.5, 1.0 - market_volatility)
        
        adaptive_speed = base_speed * profit_factor * volatility_factor
        
        # Ensure within limits
        return max(self.config.min_speed_limit, 
                  min(adaptive_speed, self.config.max_speed_limit))
    
    def _calculate_dynamic_speed(self, algorithm: str, profit: float) -> float:
        """Calculate dynamic speed based on algorithm and profit"""
        # Base speed from algorithm characteristics
        algorithm_speeds = {
            'SHA256': 1000.0,
            'Ethash': 800.0,
            'Lyra2REv2': 600.0,
            'BeamHash': 500.0,
            'CuckooCycle': 400.0
        }
        
        base_speed = algorithm_speeds.get(algorithm, 500.0)
        
        # Adjust based on profit
        if profit > self.config.dynamic_threshold:
            # High profit - use higher speed
            speed_multiplier = min(profit / self.config.dynamic_threshold, 1.5)
        else:
            # Low profit - use lower speed
            speed_multiplier = max(profit / self.config.dynamic_threshold, 0.3)
        
        dynamic_speed = base_speed * speed_multiplier
        
        # Ensure within global limits
        return max(self.config.min_speed_limit,
                  min(dynamic_speed, self.config.max_speed_limit))
    
    def update_speed_limit(self, new_limit: float, reason: str = ""):
        """Update current speed limit"""
        old_limit = self.current_speed_limit
        self.current_speed_limit = max(self.config.min_speed_limit,
                                     min(new_limit, self.config.max_speed_limit))
        
        # Record speed change
        self.speed_history.append({
            'time': time.time(),
            'old_limit': old_limit,
            'new_limit': self.current_speed_limit,
            'reason': reason
        })
        
        logger.info(f"Speed limit updated: {old_limit:.1f} -> {self.current_speed_limit:.1f} TH/s ({reason})")
    
    def adjust_speed_for_order(self, algorithm: str, profit: float, 
                             current_price: float, market_volatility: float = 0.0) -> float:
        """Adjust speed for specific order"""
        optimal_speed = self.calculate_optimal_speed(algorithm, profit, market_volatility)
        
        # Round to nearest increment
        adjusted_speed = round(optimal_speed / self.config.speed_increment) * self.config.speed_increment
        
        # Ensure within limits
        final_speed = max(self.config.min_speed_limit,
                         min(adjusted_speed, self.config.max_speed_limit))
        
        logger.debug(f"Speed adjustment for {algorithm}: {final_speed:.1f} TH/s (profit: {profit:.6f})")
        
        return final_speed
    
    def get_speed_recommendation(self, algorithm: str, profit: float, 
                               market_conditions: Dict) -> Dict:
        """Get speed recommendation with reasoning"""
        market_volatility = market_conditions.get('volatility', 0.0)
        optimal_speed = self.calculate_optimal_speed(algorithm, profit, market_volatility)
        
        recommendation = {
            'algorithm': algorithm,
            'recommended_speed': optimal_speed,
            'current_limit': self.current_speed_limit,
            'mode': self.config.mode.value,
            'reasoning': self._get_reasoning(algorithm, profit, market_volatility),
            'within_limits': optimal_speed <= self.current_speed_limit
        }
        
        return recommendation
    
    def _get_reasoning(self, algorithm: str, profit: float, volatility: float) -> str:
        """Get reasoning for speed recommendation"""
        if self.config.mode == SpeedLimitMode.FIXED:
            return f"Fixed mode: using maximum speed limit {self.config.max_speed_limit} TH/s"
        
        elif self.config.mode == SpeedLimitMode.ADAPTIVE:
            return f"Adaptive mode: profit={profit:.6f}, volatility={volatility:.3f}"
        
        elif self.config.mode == SpeedLimitMode.DYNAMIC:
            return f"Dynamic mode: algorithm={algorithm}, profit={profit:.6f}"
        
        return "Unknown mode"
    
    def get_speed_status(self) -> Dict:
        """Get current speed status"""
        return {
            'current_limit': self.current_speed_limit,
            'max_limit': self.config.max_speed_limit,
            'min_limit': self.config.min_speed_limit,
            'mode': self.config.mode.value,
            'recent_changes': len([h for h in self.speed_history 
                                 if time.time() - h['time'] < 3600])  # Last hour
        }
    
    def reset_to_maximum(self):
        """Reset speed limit to maximum"""
        self.update_speed_limit(self.config.max_speed_limit, "Reset to maximum")
    
    def reduce_speed(self, reduction_factor: float = 0.8):
        """Reduce speed limit by factor"""
        new_limit = self.current_speed_limit * reduction_factor
        self.update_speed_limit(new_limit, f"Reduced by factor {reduction_factor}")
    
    def increase_speed(self, increase_factor: float = 1.2):
        """Increase speed limit by factor"""
        new_limit = self.current_speed_limit * increase_factor
        self.update_speed_limit(new_limit, f"Increased by factor {increase_factor}")
