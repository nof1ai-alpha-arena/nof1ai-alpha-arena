"""
SQLAlchemy database models for AI Trading Bot.

This module defines the database schema for persisting trading data,
replacing the JSONL-based storage with proper relational database support.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()


class Trade(Base):
    """
    Trade history record - completed trades with entry/exit details.

    Replaces entries in diary.jsonl for actual executed trades.
    """
    __tablename__ = 'trades'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Trade identification
    asset = Column(String(20), nullable=False, index=True)  # BTC, ETH, SOL, etc.
    action = Column(String(10), nullable=False, index=True)  # buy, sell

    # Entry details
    entry_timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    entry_price = Column(Float, nullable=False)
    entry_size = Column(Float, nullable=False)  # Position size in asset units
    entry_value = Column(Float, nullable=False)  # Position value in USD

    # Exit details (nullable for open positions)
    exit_timestamp = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    exit_value = Column(Float, nullable=True)

    # P&L
    realized_pnl = Column(Float, nullable=True)  # Actual profit/loss in USD
    realized_pnl_pct = Column(Float, nullable=True)  # Percentage return

    # Risk management
    leverage = Column(Float, default=1.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # AI decision context
    llm_model = Column(String(100), nullable=True)  # e.g., "x-ai/grok-4"
    rationale = Column(Text, nullable=True)  # LLM reasoning for the trade
    reasoning_tokens = Column(Text, nullable=True)  # Full reasoning chain (JSON)

    # Execution details
    order_id = Column(String(100), nullable=True)  # Hyperliquid order ID
    fill_count = Column(Integer, default=1)  # Number of fills to complete order

    # Status tracking
    status = Column(String(20), default='open', index=True)  # open, closed, cancelled

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Indexes for common queries
    __table_args__ = (
        Index('idx_trade_asset_timestamp', 'asset', 'entry_timestamp'),
        Index('idx_trade_status_timestamp', 'status', 'entry_timestamp'),
    )

    def __repr__(self):
        return f"<Trade(id={self.id}, asset={self.asset}, action={self.action}, status={self.status})>"


class Position(Base):
    """
    Current open positions - synchronized with Hyperliquid account state.

    Tracks active positions with real-time P&L.
    """
    __tablename__ = 'positions'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Position identification
    asset = Column(String(20), nullable=False, unique=True, index=True)

    # Position details
    side = Column(String(10), nullable=False)  # long, short
    size = Column(Float, nullable=False)  # Position size in asset units
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    liquidation_price = Column(Float, nullable=True)

    # P&L
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    unrealized_pnl_pct = Column(Float, nullable=False, default=0.0)

    # Risk management
    leverage = Column(Float, default=1.0)
    margin = Column(Float, nullable=False)

    # Associated trade (if exists)
    trade_id = Column(Integer, ForeignKey('trades.id'), nullable=True)
    trade = relationship('Trade', backref='position')

    # Timestamps
    opened_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Position(id={self.id}, asset={self.asset}, side={self.side}, size={self.size})>"


class DiaryEntry(Base):
    """
    Trading diary - AI decision log including HOLD actions.

    Replaces diary.jsonl - captures all LLM decisions even when no trade occurs.
    """
    __tablename__ = 'diary_entries'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Decision details
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    asset = Column(String(20), nullable=False, index=True)
    action = Column(String(10), nullable=False, index=True)  # hold, buy, sell

    # AI reasoning
    rationale = Column(Text, nullable=False)
    llm_model = Column(String(100), nullable=True)
    reasoning_tokens = Column(Text, nullable=True)  # Full reasoning chain (JSON)

    # Market context at decision time
    price = Column(Float, nullable=True)
    indicators = Column(Text, nullable=True)  # JSON snapshot of indicators

    # Associated trade (if action resulted in trade)
    trade_id = Column(Integer, ForeignKey('trades.id'), nullable=True)
    trade = relationship('Trade', backref='diary_entry')

    # Metadata
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_diary_asset_timestamp', 'asset', 'timestamp'),
        Index('idx_diary_action_timestamp', 'action', 'timestamp'),
    )

    def __repr__(self):
        return f"<DiaryEntry(id={self.id}, asset={self.asset}, action={self.action}, timestamp={self.timestamp})>"


class BotState(Base):
    """
    Bot state snapshots for historical tracking.

    Periodically captures account state for performance analysis and equity curve.
    """
    __tablename__ = 'bot_states'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Snapshot timestamp
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)

    # Account metrics
    balance = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)  # Balance + unrealized P&L
    equity = Column(Float, nullable=False)  # Total equity

    # Performance metrics
    total_return_pct = Column(Float, nullable=False, default=0.0)
    daily_return_pct = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)

    # Position summary
    open_positions_count = Column(Integer, default=0)
    total_position_value = Column(Float, default=0.0)
    total_unrealized_pnl = Column(Float, default=0.0)

    # Trade summary
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, nullable=True)

    # Risk metrics
    max_drawdown = Column(Float, nullable=True)
    avg_profit = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)

    # Bot status
    is_running = Column(Boolean, default=False)
    trading_mode = Column(String(20), nullable=True)  # auto, manual

    # Metadata
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_state_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<BotState(id={self.id}, timestamp={self.timestamp}, balance={self.balance}, total_value={self.total_value})>"


class TradeProposal(Base):
    """
    Trade proposals for manual trading mode.

    Stores AI-generated trade recommendations awaiting user approval.
    """
    __tablename__ = 'trade_proposals'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Proposal identification
    asset = Column(String(20), nullable=False, index=True)
    action = Column(String(10), nullable=False)  # buy, sell

    # Proposal details
    proposed_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    size = Column(Float, nullable=False)
    price = Column(Float, nullable=False)  # Price at proposal time

    # Risk management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    leverage = Column(Float, default=1.0)

    # AI reasoning
    rationale = Column(Text, nullable=False)
    llm_model = Column(String(100), nullable=True)
    reasoning_tokens = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)  # 0-1 confidence score

    # Status tracking
    status = Column(String(20), default='pending', index=True)  # pending, approved, rejected, executed, failed, expired

    # User decision
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)  # User ID (future)
    rejection_reason = Column(Text, nullable=True)

    # Execution details (if approved and executed)
    executed_at = Column(DateTime, nullable=True)
    execution_price = Column(Float, nullable=True)
    trade_id = Column(Integer, ForeignKey('trades.id'), nullable=True)
    trade = relationship('Trade', backref='proposal')

    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_proposal_status_timestamp', 'status', 'proposed_at'),
        Index('idx_proposal_asset_status', 'asset', 'status'),
    )

    def __repr__(self):
        return f"<TradeProposal(id={self.id}, asset={self.asset}, action={self.action}, status={self.status})>"


class MarketData(Base):
    """
    Historical market data snapshots for backtesting and analysis.

    Optional table for future backtesting functionality.
    """
    __tablename__ = 'market_data'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Data identification
    asset = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    interval = Column(String(10), nullable=False)  # 1m, 5m, 1h, 4h, 1d

    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Additional market metrics
    open_interest = Column(Float, nullable=True)
    funding_rate = Column(Float, nullable=True)

    # Technical indicators (JSON)
    indicators = Column(Text, nullable=True)  # JSON dict of all indicators

    # Metadata
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint('asset', 'timestamp', 'interval', name='uq_market_data'),
        Index('idx_market_asset_timestamp', 'asset', 'timestamp'),
        Index('idx_market_asset_interval', 'asset', 'interval'),
    )

    def __repr__(self):
        return f"<MarketData(id={self.id}, asset={self.asset}, timestamp={self.timestamp}, close={self.close})>"


# Database initialization helper
def create_tables(engine):
    """Create all tables in the database."""
    Base.metadata.create_all(engine)
    print("[OK] Database tables created successfully")


def drop_tables(engine):
    """Drop all tables in the database (use with caution!)."""
    Base.metadata.drop_all(engine)
    print("[WARNING] All database tables dropped")
