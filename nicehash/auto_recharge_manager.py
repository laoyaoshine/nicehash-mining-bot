#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Recharge Manager
Handles automatic balance recharge when order amount is insufficient
"""

import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RechargeConfig:
    """Recharge configuration"""
    enabled: bool = True
    threshold: float = 0.01  # Minimum balance threshold
    recharge_amount: float = 0.1  # Amount to recharge
    min_balance_threshold: float = 0.05  # Minimum balance to maintain
    max_recharge_per_day: int = 5  # Maximum recharges per day
    cooldown_minutes: int = 30  # Cooldown between recharges

class AutoRechargeManager:
    """Auto recharge manager for NiceHash orders"""
    
    def __init__(self, config: RechargeConfig):
        self.config = config
        self.recharge_history = []  # Track recharge history
        self.last_recharge_time = 0
        self.daily_recharge_count = 0
        self.last_reset_date = None
    
    def check_balance_sufficient(self, required_amount: float, current_balance: float) -> bool:
        """Check if balance is sufficient for order"""
        return current_balance >= required_amount
    
    def should_recharge(self, current_balance: float, required_amount: float) -> Tuple[bool, str]:
        """Determine if recharge is needed and why"""
        if not self.config.enabled:
            return False, "Auto recharge disabled"
        
        # Check if balance is above minimum threshold
        if current_balance >= self.config.min_balance_threshold:
            return False, "Balance above minimum threshold"
        
        # Check daily recharge limit
        if self._is_daily_limit_reached():
            return False, "Daily recharge limit reached"
        
        # Check cooldown period
        if self._is_in_cooldown():
            return False, "In cooldown period"
        
        # Check if recharge would be sufficient
        if current_balance + self.config.recharge_amount < required_amount:
            return False, "Recharge amount insufficient"
        
        return True, "Recharge needed"
    
    def calculate_recharge_amount(self, current_balance: float, required_amount: float) -> float:
        """Calculate optimal recharge amount"""
        if not self.config.enabled:
            return 0.0
        
        # Calculate minimum needed
        min_needed = required_amount - current_balance
        
        # Use configured recharge amount or minimum needed, whichever is larger
        recharge_amount = max(self.config.recharge_amount, min_needed)
        
        # Ensure we don't exceed reasonable limits
        max_recharge = min(recharge_amount, 1.0)  # Cap at 1 BTC
        
        return max_recharge
    
    def execute_recharge(self, amount: float) -> bool:
        """Execute recharge operation"""
        try:
            # Check cooldown
            if self._is_in_cooldown():
                logger.warning(f"Recharge blocked: in cooldown period")
                return False
            
            # Check daily limit
            if self._is_daily_limit_reached():
                logger.warning(f"Recharge blocked: daily limit reached")
                return False
            
            # Record recharge
            recharge_time = time.time()
            self.recharge_history.append({
                'time': recharge_time,
                'amount': amount,
                'success': True
            })
            
            self.last_recharge_time = recharge_time
            self.daily_recharge_count += 1
            
            logger.info(f"Auto recharge executed: {amount:.6f} BTC")
            return True
            
        except Exception as e:
            logger.error(f"Recharge execution failed: {e}")
            return False
    
    def get_account_balance(self) -> float:
        """Get current account balance (placeholder for API integration)"""
        # This would integrate with NiceHash API to get actual balance
        # For now, return a mock balance
        return 0.05  # Mock balance
    
    def recharge_account(self, amount: float) -> bool:
        """Recharge account with specified amount (placeholder for API integration)"""
        # This would integrate with NiceHash API to recharge account
        # For now, simulate successful recharge
        logger.info(f"Simulating account recharge: {amount:.6f} BTC")
        return True
    
    def _is_daily_limit_reached(self) -> bool:
        """Check if daily recharge limit is reached"""
        current_date = time.strftime("%Y-%m-%d")
        
        # Reset daily count if new day
        if self.last_reset_date != current_date:
            self.daily_recharge_count = 0
            self.last_reset_date = current_date
        
        return self.daily_recharge_count >= self.config.max_recharge_per_day
    
    def _is_in_cooldown(self) -> bool:
        """Check if in cooldown period"""
        if self.last_recharge_time == 0:
            return False
        
        cooldown_seconds = self.config.cooldown_minutes * 60
        time_since_last = time.time() - self.last_recharge_time
        
        return time_since_last < cooldown_seconds
    
    def get_recharge_status(self) -> Dict:
        """Get current recharge status"""
        current_balance = self.get_account_balance()
        
        return {
            'enabled': self.config.enabled,
            'current_balance': current_balance,
            'daily_recharge_count': self.daily_recharge_count,
            'last_recharge_time': self.last_recharge_time,
            'in_cooldown': self._is_in_cooldown(),
            'daily_limit_reached': self._is_daily_limit_reached(),
            'cooldown_remaining': max(0, self.config.cooldown_minutes * 60 - (time.time() - self.last_recharge_time)) if self.last_recharge_time > 0 else 0
        }
    
    def handle_insufficient_balance(self, required_amount: float) -> bool:
        """Handle insufficient balance scenario"""
        current_balance = self.get_account_balance()
        
        logger.warning(f"Insufficient balance: {current_balance:.6f} BTC < {required_amount:.6f} BTC")
        
        should_recharge, reason = self.should_recharge(current_balance, required_amount)
        
        if not should_recharge:
            logger.info(f"Recharge not needed: {reason}")
            return False
        
        recharge_amount = self.calculate_recharge_amount(current_balance, required_amount)
        
        if recharge_amount <= 0:
            logger.error("Cannot calculate valid recharge amount")
            return False
        
        logger.info(f"Attempting auto recharge: {recharge_amount:.6f} BTC")
        
        # Execute recharge
        if self.execute_recharge(recharge_amount):
            # Simulate actual recharge (in real implementation, this would call NiceHash API)
            if self.recharge_account(recharge_amount):
                logger.info(f"Auto recharge successful: {recharge_amount:.6f} BTC")
                return True
            else:
                logger.error("Recharge API call failed")
                return False
        else:
            logger.error("Recharge execution failed")
            return False
