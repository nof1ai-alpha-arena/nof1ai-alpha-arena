"""
Trade Proposal Model - AI recommendations for manual approval
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
import uuid


@dataclass
class TradeProposal:
    """
    AI-generated trade proposal waiting for user approval.
    
    Used in manual trading mode where AI suggests trades but user must confirm.
    """
    
    # Identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    # Asset and action
    asset: str = ""
    action: str = ""  # "buy" / "sell" / "close" / "hold"
    
    # Confidence and risk
    confidence: float = 0.0  # 0-100
    risk_reward: Optional[float] = None
    
    # Trade parameters
    entry_price: float = 0.0
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    size: float = 0.0
    allocation: float = 0.0  # Dollar amount
    
    # AI reasoning
    rationale: str = ""
    market_conditions: Optional[dict] = None
    
    # Status tracking
    status: str = "pending"  # pending / approved / rejected / executed / failed
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    
    # Execution results (filled after execution)
    execution_price: Optional[float] = None
    execution_error: Optional[str] = None
    
    def approve(self) -> bool:
        """Mark proposal as approved"""
        if self.status != "pending":
            return False
        
        self.status = "approved"
        self.approved_at = datetime.now(UTC)
        return True
    
    def reject(self, reason: Optional[str] = None) -> bool:
        """Mark proposal as rejected"""
        if self.status != "pending":
            return False
        
        self.status = "rejected"
        self.rejected_at = datetime.now(UTC)
        if reason:
            self.execution_error = reason
        return True
    
    def mark_executed(self, execution_price: float):
        """Mark proposal as successfully executed"""
        self.status = "executed"
        self.executed_at = datetime.now(UTC)
        self.execution_price = execution_price
    
    def mark_failed(self, error: str):
        """Mark proposal as failed to execute"""
        self.status = "failed"
        self.executed_at = datetime.now(UTC)
        self.execution_error = error
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'asset': self.asset,
            'action': self.action,
            'confidence': self.confidence,
            'risk_reward': self.risk_reward,
            'entry_price': self.entry_price,
            'tp_price': self.tp_price,
            'sl_price': self.sl_price,
            'size': self.size,
            'allocation': self.allocation,
            'rationale': self.rationale,
            'market_conditions': self.market_conditions,
            'status': self.status,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_price': self.execution_price,
            'execution_error': self.execution_error
        }
    
    @property
    def is_pending(self) -> bool:
        """Check if proposal is pending approval"""
        return self.status == "pending"
    
    @property
    def potential_gain(self) -> Optional[float]:
        """Calculate potential gain if TP is hit"""
        if not self.tp_price or not self.entry_price:
            return None
        
        if self.action == "buy":
            return ((self.tp_price - self.entry_price) / self.entry_price) * 100
        elif self.action == "sell":
            return ((self.entry_price - self.tp_price) / self.entry_price) * 100
        return None
    
    @property
    def potential_loss(self) -> Optional[float]:
        """Calculate potential loss if SL is hit"""
        if not self.sl_price or not self.entry_price:
            return None
        
        if self.action == "buy":
            return ((self.sl_price - self.entry_price) / self.entry_price) * 100
        elif self.action == "sell":
            return ((self.entry_price - self.sl_price) / self.entry_price) * 100
        return None
