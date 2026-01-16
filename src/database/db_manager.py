"""
Database Manager for AI Trading Bot.

Provides high-level interface for database operations,
replacing JSONL-based storage with SQLite/SQLAlchemy.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, desc, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import (
    Base,
    Trade,
    Position,
    DiaryEntry,
    BotState,
    TradeProposal,
    MarketData,
    create_tables,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    High-level database manager for all trading data persistence.

    Provides clean API for CRUD operations on all models with
    automatic session management and error handling.
    """

    def __init__(self, db_url: str = None):
        """
        Initialize database manager.

        Args:
            db_url: SQLAlchemy database URL. Defaults to sqlite:///data/bot.db
        """
        if db_url is None:
            # Default to SQLite in data/ directory
            db_path = os.path.join('data', 'bot.db')
            os.makedirs('data', exist_ok=True)
            db_url = f'sqlite:///{db_path}'

        self.engine = create_engine(
            db_url,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,  # Verify connections before using
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Create tables if they don't exist
        create_tables(self.engine)
        logger.info(f"Database initialized: {db_url}")

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope around a series of operations.

        Usage:
            with db_manager.session_scope() as session:
                session.add(trade)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    # ==================== TRADE OPERATIONS ====================

    def create_trade(
        self,
        asset: str,
        action: str,
        entry_price: float,
        entry_size: float,
        entry_value: float,
        leverage: float = 1.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        llm_model: Optional[str] = None,
        rationale: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> Trade:
        """Create a new trade record."""
        with self.session_scope() as session:
            trade = Trade(
                asset=asset,
                action=action,
                entry_timestamp=datetime.utcnow(),
                entry_price=entry_price,
                entry_size=entry_size,
                entry_value=entry_value,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                llm_model=llm_model,
                rationale=rationale,
                order_id=order_id,
                status='open',
            )
            session.add(trade)
            session.flush()
            session.refresh(trade)
            logger.info(f"Created trade: {trade.id} ({asset} {action})")
            return trade

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        exit_value: float,
        realized_pnl: float,
        realized_pnl_pct: float,
    ) -> Trade:
        """Close an existing trade."""
        with self.session_scope() as session:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                raise ValueError(f"Trade {trade_id} not found")

            trade.exit_timestamp = datetime.utcnow()
            trade.exit_price = exit_price
            trade.exit_value = exit_value
            trade.realized_pnl = realized_pnl
            trade.realized_pnl_pct = realized_pnl_pct
            trade.status = 'closed'

            session.flush()
            session.refresh(trade)
            logger.info(f"Closed trade: {trade_id} (PnL: {realized_pnl:.2f}, {realized_pnl_pct:.2f}%)")
            return trade

    def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get a trade by ID."""
        with self.session_scope() as session:
            return session.query(Trade).filter(Trade.id == trade_id).first()

    def get_trades(
        self,
        asset: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Trade]:
        """Get trades with optional filtering."""
        with self.session_scope() as session:
            query = session.query(Trade)

            if asset:
                query = query.filter(Trade.asset == asset)
            if status:
                query = query.filter(Trade.status == status)

            query = query.order_by(desc(Trade.entry_timestamp))
            query = query.limit(limit).offset(offset)

            return query.all()

    def get_open_trades(self, asset: Optional[str] = None) -> List[Trade]:
        """Get all open trades."""
        return self.get_trades(asset=asset, status='open', limit=1000)

    def get_trade_stats(self) -> Dict[str, Any]:
        """Get aggregate trade statistics."""
        with self.session_scope() as session:
            closed_trades = session.query(Trade).filter(Trade.status == 'closed').all()

            if not closed_trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'total_pnl': 0.0,
                    'avg_profit': 0.0,
                    'avg_loss': 0.0,
                    'profit_factor': 0.0,
                }

            total_trades = len(closed_trades)
            winning_trades = [t for t in closed_trades if t.realized_pnl and t.realized_pnl > 0]
            losing_trades = [t for t in closed_trades if t.realized_pnl and t.realized_pnl < 0]

            total_pnl = sum(t.realized_pnl for t in closed_trades if t.realized_pnl)
            avg_profit = sum(t.realized_pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(t.realized_pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0

            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            profit_factor = abs(sum(t.realized_pnl for t in winning_trades) / sum(t.realized_pnl for t in losing_trades)) if losing_trades and sum(t.realized_pnl for t in losing_trades) != 0 else 0

            return {
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
            }

    # ==================== POSITION OPERATIONS ====================

    def upsert_position(
        self,
        asset: str,
        side: str,
        size: float,
        entry_price: float,
        current_price: float,
        unrealized_pnl: float,
        unrealized_pnl_pct: float,
        leverage: float = 1.0,
        margin: float = 0.0,
        liquidation_price: Optional[float] = None,
        trade_id: Optional[int] = None,
    ) -> Position:
        """Create or update a position."""
        with self.session_scope() as session:
            position = session.query(Position).filter(Position.asset == asset).first()

            if position:
                # Update existing position
                position.side = side
                position.size = size
                position.entry_price = entry_price
                position.current_price = current_price
                position.unrealized_pnl = unrealized_pnl
                position.unrealized_pnl_pct = unrealized_pnl_pct
                position.leverage = leverage
                position.margin = margin
                position.liquidation_price = liquidation_price
                position.trade_id = trade_id
                logger.debug(f"Updated position: {asset}")
            else:
                # Create new position
                position = Position(
                    asset=asset,
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    leverage=leverage,
                    margin=margin,
                    liquidation_price=liquidation_price,
                    trade_id=trade_id,
                    opened_at=datetime.utcnow(),
                )
                session.add(position)
                logger.info(f"Created position: {asset}")

            session.flush()
            session.refresh(position)
            return position

    def close_position(self, asset: str) -> None:
        """Close (delete) a position."""
        with self.session_scope() as session:
            position = session.query(Position).filter(Position.asset == asset).first()
            if position:
                session.delete(position)
                logger.info(f"Closed position: {asset}")

    def get_position(self, asset: str) -> Optional[Position]:
        """Get a position by asset."""
        with self.session_scope() as session:
            return session.query(Position).filter(Position.asset == asset).first()

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        with self.session_scope() as session:
            return session.query(Position).order_by(Position.opened_at).all()

    # ==================== DIARY OPERATIONS ====================

    def create_diary_entry(
        self,
        asset: str,
        action: str,
        rationale: str,
        llm_model: Optional[str] = None,
        price: Optional[float] = None,
        indicators: Optional[str] = None,
        trade_id: Optional[int] = None,
    ) -> DiaryEntry:
        """Create a new diary entry."""
        with self.session_scope() as session:
            entry = DiaryEntry(
                timestamp=datetime.utcnow(),
                asset=asset,
                action=action,
                rationale=rationale,
                llm_model=llm_model,
                price=price,
                indicators=indicators,
                trade_id=trade_id,
            )
            session.add(entry)
            session.flush()
            session.refresh(entry)
            logger.debug(f"Created diary entry: {asset} {action}")
            return entry

    def get_diary_entries(
        self,
        asset: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DiaryEntry]:
        """Get diary entries with optional filtering."""
        with self.session_scope() as session:
            query = session.query(DiaryEntry)

            if asset:
                query = query.filter(DiaryEntry.asset == asset)
            if action:
                query = query.filter(DiaryEntry.action == action)

            query = query.order_by(desc(DiaryEntry.timestamp))
            query = query.limit(limit).offset(offset)

            return query.all()

    def get_recent_diary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent diary entries in format compatible with bot_engine."""
        entries = self.get_diary_entries(limit=limit)
        return [
            {
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'asset': entry.asset,
                'action': entry.action,
                'rationale': entry.rationale,
            }
            for entry in entries
        ]

    # ==================== BOT STATE OPERATIONS ====================

    def save_bot_state(
        self,
        balance: float,
        total_value: float,
        equity: float,
        total_return_pct: float,
        sharpe_ratio: Optional[float] = None,
        open_positions_count: int = 0,
        total_position_value: float = 0.0,
        total_unrealized_pnl: float = 0.0,
        is_running: bool = False,
        trading_mode: Optional[str] = None,
    ) -> BotState:
        """Save a snapshot of bot state."""
        with self.session_scope() as session:
            # Get trade stats
            stats = self.get_trade_stats()

            state = BotState(
                timestamp=datetime.utcnow(),
                balance=balance,
                total_value=total_value,
                equity=equity,
                total_return_pct=total_return_pct,
                sharpe_ratio=sharpe_ratio,
                open_positions_count=open_positions_count,
                total_position_value=total_position_value,
                total_unrealized_pnl=total_unrealized_pnl,
                total_trades=stats['total_trades'],
                winning_trades=stats['winning_trades'],
                losing_trades=stats['losing_trades'],
                win_rate=stats['win_rate'],
                avg_profit=stats['avg_profit'],
                avg_loss=stats['avg_loss'],
                profit_factor=stats['profit_factor'],
                is_running=is_running,
                trading_mode=trading_mode,
            )
            session.add(state)
            session.flush()
            session.refresh(state)
            logger.debug(f"Saved bot state: balance={balance:.2f}, total_value={total_value:.2f}")
            return state

    def get_latest_bot_state(self) -> Optional[BotState]:
        """Get the most recent bot state."""
        with self.session_scope() as session:
            return session.query(BotState).order_by(desc(BotState.timestamp)).first()

    def get_bot_states(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[BotState]:
        """Get bot states within a date range."""
        with self.session_scope() as session:
            query = session.query(BotState)

            if start_date:
                query = query.filter(BotState.timestamp >= start_date)
            if end_date:
                query = query.filter(BotState.timestamp <= end_date)

            query = query.order_by(desc(BotState.timestamp))
            query = query.limit(limit)

            return query.all()

    def get_equity_curve(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get equity curve data for charting."""
        start_date = datetime.utcnow() - timedelta(days=days)
        states = self.get_bot_states(start_date=start_date, limit=10000)

        return [
            {
                'timestamp': state.timestamp.isoformat() if state.timestamp else None,
                'equity': state.equity,
                'balance': state.balance,
                'total_value': state.total_value,
            }
            for state in reversed(states)
        ]

    # ==================== TRADE PROPOSAL OPERATIONS ====================

    def create_trade_proposal(
        self,
        asset: str,
        action: str,
        size: float,
        price: float,
        rationale: str,
        llm_model: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        leverage: float = 1.0,
        confidence: Optional[float] = None,
    ) -> TradeProposal:
        """Create a new trade proposal."""
        with self.session_scope() as session:
            proposal = TradeProposal(
                asset=asset,
                action=action,
                proposed_at=datetime.utcnow(),
                size=size,
                price=price,
                rationale=rationale,
                llm_model=llm_model,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=leverage,
                confidence=confidence,
                status='pending',
            )
            session.add(proposal)
            session.flush()
            session.refresh(proposal)
            logger.info(f"Created trade proposal: {proposal.id} ({asset} {action})")
            return proposal

    def approve_proposal(self, proposal_id: int) -> TradeProposal:
        """Approve a trade proposal."""
        with self.session_scope() as session:
            proposal = session.query(TradeProposal).filter(TradeProposal.id == proposal_id).first()
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found")

            proposal.status = 'approved'
            proposal.reviewed_at = datetime.utcnow()

            session.flush()
            session.refresh(proposal)
            logger.info(f"Approved proposal: {proposal_id}")
            return proposal

    def reject_proposal(self, proposal_id: int, reason: Optional[str] = None) -> TradeProposal:
        """Reject a trade proposal."""
        with self.session_scope() as session:
            proposal = session.query(TradeProposal).filter(TradeProposal.id == proposal_id).first()
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found")

            proposal.status = 'rejected'
            proposal.reviewed_at = datetime.utcnow()
            proposal.rejection_reason = reason

            session.flush()
            session.refresh(proposal)
            logger.info(f"Rejected proposal: {proposal_id}")
            return proposal

    def execute_proposal(
        self,
        proposal_id: int,
        execution_price: float,
        trade_id: int,
    ) -> TradeProposal:
        """Mark a proposal as executed."""
        with self.session_scope() as session:
            proposal = session.query(TradeProposal).filter(TradeProposal.id == proposal_id).first()
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found")

            proposal.status = 'executed'
            proposal.executed_at = datetime.utcnow()
            proposal.execution_price = execution_price
            proposal.trade_id = trade_id

            session.flush()
            session.refresh(proposal)
            logger.info(f"Executed proposal: {proposal_id}")
            return proposal

    def get_pending_proposals(self, asset: Optional[str] = None) -> List[TradeProposal]:
        """Get all pending trade proposals."""
        with self.session_scope() as session:
            query = session.query(TradeProposal).filter(TradeProposal.status == 'pending')

            if asset:
                query = query.filter(TradeProposal.asset == asset)

            query = query.order_by(desc(TradeProposal.proposed_at))

            return query.all()

    # ==================== UTILITY OPERATIONS ====================

    def migrate_jsonl_diary(self, jsonl_path: str = 'data/diary.jsonl'):
        """
        Migrate existing JSONL diary to database.

        Args:
            jsonl_path: Path to diary.jsonl file
        """
        import json

        if not os.path.exists(jsonl_path):
            logger.warning(f"JSONL file not found: {jsonl_path}")
            return 0

        count = 0
        with open(jsonl_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())

                    # Parse timestamp
                    timestamp_str = entry.get('timestamp', '')
                    if timestamp_str:
                        # Handle both ISO format and timestamp
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        except:
                            timestamp = datetime.utcnow()
                    else:
                        timestamp = datetime.utcnow()

                    # Create diary entry
                    with self.session_scope() as session:
                        diary_entry = DiaryEntry(
                            timestamp=timestamp,
                            asset=entry.get('asset', 'UNKNOWN'),
                            action=entry.get('action', 'hold'),
                            rationale=entry.get('rationale', ''),
                        )
                        session.add(diary_entry)
                        count += 1

                except Exception as e:
                    logger.error(f"Error migrating JSONL entry: {e}")
                    continue

        logger.info(f"[OK] Migrated {count} diary entries from {jsonl_path}")
        return count

    def get_database_stats(self) -> Dict[str, int]:
        """Get statistics about database contents."""
        with self.session_scope() as session:
            return {
                'trades': session.query(Trade).count(),
                'open_trades': session.query(Trade).filter(Trade.status == 'open').count(),
                'closed_trades': session.query(Trade).filter(Trade.status == 'closed').count(),
                'positions': session.query(Position).count(),
                'diary_entries': session.query(DiaryEntry).count(),
                'bot_states': session.query(BotState).count(),
                'trade_proposals': session.query(TradeProposal).count(),
                'pending_proposals': session.query(TradeProposal).filter(TradeProposal.status == 'pending').count(),
            }


# Global database manager instance (singleton pattern)
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_url: str = None) -> DatabaseManager:
    """
    Get or create global database manager instance.

    Args:
        db_url: SQLAlchemy database URL (optional)

    Returns:
        DatabaseManager instance
    """
    global _db_manager

    if _db_manager is None:
        _db_manager = DatabaseManager(db_url=db_url)

    return _db_manager
