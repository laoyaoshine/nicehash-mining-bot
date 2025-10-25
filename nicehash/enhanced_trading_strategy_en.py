#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Trading Strategy Module
Implements dynamic price monitoring, smart order strategy and hashrate guarantee mechanism
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class PriceVolatility(Enum):
    """Price volatility levels"""
    LOW = "low"          # Low volatility: price change < 5%
    MEDIUM = "medium"    # Medium volatility: price change 5-15%
    HIGH = "high"        # High volatility: price change > 15%

class OrderPriority(Enum):
    """Order priority levels"""
    CRITICAL = 1    # Critical: high profit algorithms
    HIGH = 2        # High: medium profit algorithms
    NORMAL = 3      # Normal: low profit algorithms
    LOW = 4         # Low: micro profit algorithms

@dataclass
class PriceData:
    """Price data"""
    algorithm: str
    price: float
    timestamp: float
    market: str = "DEFAULT"
    volatility: PriceVolatility = PriceVolatility.LOW

@dataclass
class OrderStrategy:
    """Order strategy"""
    algorithm: str
    base_price: float
    target_price: float
    max_price: float
    priority: OrderPriority
    market: str
    amount: float
    price_adjustment_factor: float = 1.001  # Price micro-adjustment factor

class DynamicPriceMonitor:
    """Dynamic price monitor"""
    
    def __init__(self, base_check_interval: int = 60):
        self.base_check_interval = base_check_interval
        self.price_history = {}  # {algorithm: [PriceData]}
        self.volatility_thresholds = {
            PriceVolatility.LOW: 0.05,      # 5%
            PriceVolatility.MEDIUM: 0.15,   # 15%
            PriceVolatility.HIGH: 0.30      # 30%
        }
        self.adaptive_intervals = {
            PriceVolatility.LOW: 120,       # 2 minutes
            PriceVolatility.MEDIUM: 60,     # 1 minute
            PriceVolatility.HIGH: 30       # 30 seconds
        }
    
    def add_price_data(self, algorithm: str, price: float, market: str = "DEFAULT"):
        """Add price data"""
        if algorithm not in self.price_history:
            self.price_history[algorithm] = []
        
        price_data = PriceData(
            algorithm=algorithm,
            price=price,
            timestamp=time.time(),
            market=market
        )
        
        self.price_history[algorithm].append(price_data)
        
        # Keep only recent 100 records
        if len(self.price_history[algorithm]) > 100:
            self.price_history[algorithm] = self.price_history[algorithm][-100:]
        
        # Calculate volatility
        price_data.volatility = self._calculate_volatility(algorithm)
    
    def update_prices(self, prices: Dict[str, float]):
        """Batch update price data"""
        for algorithm, price in prices.items():
            self.add_price_data(algorithm, price)
    
    def _calculate_volatility(self, algorithm: str) -> PriceVolatility:
        """Calculate price volatility"""
        if algorithm not in self.price_history or len(self.price_history[algorithm]) < 5:
            return PriceVolatility.LOW
        
        prices = [p.price for p in self.price_history[algorithm][-10:]]  # Recent 10 prices
        if len(prices) < 2:
            return PriceVolatility.LOW
        
        # Calculate price change rate
        price_changes = []
        for i in range(1, len(prices)):
            change_rate = abs(prices[i] - prices[i-1]) / prices[i-1]
            price_changes.append(change_rate)
        
        avg_change = statistics.mean(price_changes)
        
        if avg_change < self.volatility_thresholds[PriceVolatility.LOW]:
            return PriceVolatility.LOW
        elif avg_change < self.volatility_thresholds[PriceVolatility.MEDIUM]:
            return PriceVolatility.MEDIUM
        else:
            return PriceVolatility.HIGH
    
    def get_adaptive_check_interval(self, algorithm: str) -> int:
        """Get adaptive check interval"""
        if algorithm not in self.price_history:
            return self.base_check_interval
        
        latest_data = self.price_history[algorithm][-1] if self.price_history[algorithm] else None
        if not latest_data:
            return self.base_check_interval
        
        return self.adaptive_intervals.get(latest_data.volatility, self.base_check_interval)
    
    def get_price_trend(self, algorithm: str, lookback_periods: int = 5) -> str:
        """Get price trend"""
        if algorithm not in self.price_history or len(self.price_history[algorithm]) < lookback_periods:
            return "unknown"
        
        recent_prices = [p.price for p in self.price_history[algorithm][-lookback_periods:]]
        
        if len(recent_prices) < 2:
            return "unknown"
        
        # Simple linear trend analysis
        first_price = recent_prices[0]
        last_price = recent_prices[-1]
        change_rate = (last_price - first_price) / first_price
        
        if change_rate > 0.05:  # Rising more than 5%
            return "rising"
        elif change_rate < -0.05:  # Falling more than 5%
            return "falling"
        else:
            return "stable"

class SmartOrderManager:
    """Smart order manager"""
    
    def __init__(self, max_orders: int = 10):
        self.max_orders = max_orders
        self.active_orders = {}  # {order_id: OrderStrategy}
        self.order_history = []
        self.price_monitor = DynamicPriceMonitor()
    
    def calculate_order_strategy(self, algorithm: str, base_price: float, 
                               net_profit: float, market: str = "DEFAULT") -> Optional[OrderStrategy]:
        """Calculate order strategy"""
        try:
            # Add price data to monitor
            self.price_monitor.add_price_data(algorithm, base_price, market)
            
            # Determine order priority
            priority = self._determine_priority(net_profit)
            
            # Calculate target price (price micro-adjustment strategy)
            target_price = self._calculate_target_price(algorithm, base_price, priority)
            
            # Calculate max price (stop-loss price)
            max_price = self._calculate_max_price(base_price, net_profit)
            
            # Calculate order amount
            amount = self._calculate_order_amount(net_profit, priority)
            
            # Price micro-adjustment factor
            adjustment_factor = self._get_price_adjustment_factor(algorithm, priority)
            
            return OrderStrategy(
                algorithm=algorithm,
                base_price=base_price,
                target_price=target_price,
                max_price=max_price,
                priority=priority,
                market=market,
                amount=amount,
                price_adjustment_factor=adjustment_factor
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate order strategy: {e}")
            return None
    
    def _determine_priority(self, net_profit: float) -> OrderPriority:
        """Determine order priority"""
        if net_profit > 0.01:  # High profit
            return OrderPriority.CRITICAL
        elif net_profit > 0.005:  # Medium profit
            return OrderPriority.HIGH
        elif net_profit > 0.001:  # Low profit
            return OrderPriority.NORMAL
        else:  # Micro profit
            return OrderPriority.LOW
    
    def _calculate_target_price(self, algorithm: str, base_price: float, 
                              priority: OrderPriority) -> float:
        """Calculate target price (price micro-adjustment strategy)"""
        # Get price trend
        trend = self.price_monitor.get_price_trend(algorithm)
        
        # Base micro-adjustment factor
        base_adjustment = 1.001  # 0.1% micro-adjustment
        
        # Adjust based on priority
        priority_adjustments = {
            OrderPriority.CRITICAL: 1.005,   # 0.5% micro-adjustment
            OrderPriority.HIGH: 1.003,       # 0.3% micro-adjustment
            OrderPriority.NORMAL: 1.001,     # 0.1% micro-adjustment
            OrderPriority.LOW: 1.0005        # 0.05% micro-adjustment
        }
        
        adjustment = priority_adjustments.get(priority, base_adjustment)
        
        # Adjust based on trend
        if trend == "rising":
            adjustment *= 1.002  # Slightly increase price when rising
        elif trend == "falling":
            adjustment *= 0.999  # Slightly decrease price when falling
        
        return base_price * adjustment
    
    def _calculate_max_price(self, base_price: float, net_profit: float) -> float:
        """Calculate max price (stop-loss price)"""
        # Max price = base price * (1 + net profit ratio * 0.5)
        # This ensures profit even if price rises
        profit_ratio = min(net_profit / base_price, 0.1)  # Limit to 10%
        max_price = base_price * (1 + profit_ratio * 0.5)
        return max_price
    
    def _calculate_order_amount(self, net_profit: float, priority: OrderPriority) -> float:
        """Calculate order amount"""
        # Base amount
        base_amount = 0.001
        
        # Adjust based on profit and priority
        profit_multiplier = min(net_profit * 100, 10)  # Max 10x
        priority_multipliers = {
            OrderPriority.CRITICAL: 2.0,
            OrderPriority.HIGH: 1.5,
            OrderPriority.NORMAL: 1.0,
            OrderPriority.LOW: 0.5
        }
        
        multiplier = priority_multipliers.get(priority, 1.0)
        return base_amount * profit_multiplier * multiplier
    
    def _get_price_adjustment_factor(self, algorithm: str, priority: OrderPriority) -> float:
        """Get price adjustment factor"""
        # Get price volatility
        volatility = self.price_monitor._calculate_volatility(algorithm)
        
        # Base adjustment factors
        base_factors = {
            OrderPriority.CRITICAL: 1.002,
            OrderPriority.HIGH: 1.0015,
            OrderPriority.NORMAL: 1.001,
            OrderPriority.LOW: 1.0005
        }
        
        base_factor = base_factors.get(priority, 1.001)
        
        # Adjust based on volatility
        volatility_multipliers = {
            PriceVolatility.LOW: 1.0,
            PriceVolatility.MEDIUM: 1.2,
            PriceVolatility.HIGH: 1.5
        }
        
        multiplier = volatility_multipliers.get(volatility, 1.0)
        return base_factor * multiplier
    
    def should_update_order(self, order_id: str, current_price: float) -> bool:
        """Check if order needs update"""
        if order_id not in self.active_orders:
            return False
        
        strategy = self.active_orders[order_id]
        
        # Update if current price is below target price
        if current_price < strategy.target_price:
            return True
        
        # Update if current price exceeds max price
        if current_price > strategy.max_price:
            return True
        
        return False
    
    def should_create_order(self, algorithm: str, profit: float, price: float, has_valid_api: bool = True) -> bool:
        """Check if should create order"""
        # Don't create orders if no valid API
        if not has_valid_api:
            return False
            
        # Check if exceeds max order count
        if len(self.active_orders) >= self.max_orders:
            return False
        
        # Check if already has order for this algorithm
        for order_id, strategy in self.active_orders.items():
            if strategy.algorithm == algorithm:
                return False
        
        # Check if profit is sufficient
        return profit > 0.001  # Min profit threshold
    
    def calculate_target_price(self, algorithm: str, base_price: float) -> float:
        """Calculate target price"""
        strategy = self.calculate_order_strategy(algorithm, base_price, 0.01)  # Assume 1% profit
        return strategy.target_price
    
    def add_order(self, order_id: str, algorithm: str, target_price: float, base_price: float):
        """Add order to manager"""
        strategy = self.calculate_order_strategy(algorithm, base_price, 0.01)
        strategy.target_price = target_price
        self.active_orders[order_id] = strategy
    
    def update_orders(self, current_prices: Dict[str, float]):
        """Update order status"""
        for order_id, strategy in list(self.active_orders.items()):
            if strategy.algorithm in current_prices:
                current_price = current_prices[strategy.algorithm]
                if self.should_update_order(order_id, current_price):
                    # Add order update logic here
                    pass
    
    def get_adaptive_check_interval(self) -> int:
        """Get adaptive check interval"""
        if not self.active_orders:
            return 60  # Default 1 minute
        
        # Get minimum check interval for all active algorithms
        min_interval = 60
        for strategy in self.active_orders.values():
            interval = self.price_monitor.get_adaptive_check_interval(strategy.algorithm)
            min_interval = min(min_interval, interval)
        
        return min_interval

class HashrateGuaranteeManager:
    """Hashrate guarantee manager"""
    
    def __init__(self, min_profitable_algorithms: int = 3):
        self.min_profitable_algorithms = min_profitable_algorithms
        self.backup_algorithms = []
        self.algorithm_performance = {}  # {algorithm: performance_score}
    
    def select_primary_algorithms(self, profitable_algorithms: List[Tuple[str, str, float, float]]) -> List[Tuple[str, str, float, float]]:
        """Select primary algorithms"""
        # Sort by net profit
        sorted_algorithms = sorted(profitable_algorithms, key=lambda x: x[3], reverse=True)
        
        # Select first N algorithms as primary
        primary_count = min(self.min_profitable_algorithms, len(sorted_algorithms))
        primary_algorithms = sorted_algorithms[:primary_count]
        
        # Rest as backup algorithms
        self.backup_algorithms = sorted_algorithms[primary_count:]
        
        logger.info(f"Selected {len(primary_algorithms)} primary algorithms, {len(self.backup_algorithms)} backup algorithms")
        
        return primary_algorithms
    
    def select_algorithms(self, profit_ranking: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select algorithms for mining"""
        selected = []
        
        # Select top profitable algorithms
        for i, algorithm_data in enumerate(profit_ranking[:self.min_profitable_algorithms]):
            selected.append(algorithm_data)
        
        return selected
    
    def get_backup_algorithm(self, failed_algorithm: str) -> Optional[Tuple[str, str, float, float]]:
        """Get backup algorithm"""
        if not self.backup_algorithms:
            return None
        
        # Select most profitable backup algorithm
        best_backup = max(self.backup_algorithms, key=lambda x: x[3])
        self.backup_algorithms.remove(best_backup)
        
        logger.info(f"Selected backup algorithm {best_backup[0]} for failed algorithm {failed_algorithm}")
        return best_backup
    
    def update_algorithm_performance(self, algorithm: str, success: bool, profit: float):
        """Update algorithm performance"""
        if algorithm not in self.algorithm_performance:
            self.algorithm_performance[algorithm] = {'success_count': 0, 'total_count': 0, 'total_profit': 0.0}
        
        perf = self.algorithm_performance[algorithm]
        perf['total_count'] += 1
        if success:
            perf['success_count'] += 1
        perf['total_profit'] += profit
        
        # Calculate performance score
        success_rate = perf['success_count'] / perf['total_count']
        avg_profit = perf['total_profit'] / perf['total_count']
        perf['performance_score'] = success_rate * avg_profit * 1000  # Amplification factor
    
    def get_algorithm_ranking(self) -> List[Tuple[str, float]]:
        """Get algorithm ranking"""
        return sorted(
            [(alg, perf['performance_score']) for alg, perf in self.algorithm_performance.items()],
            key=lambda x: x[1],
            reverse=True
        )
