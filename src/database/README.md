# Database Layer - AI Trading Bot

SQLAlchemy-based persistence layer for AI Trading Bot, replacing JSONL file storage.

## Overview

The database layer provides structured, queryable storage for all trading data:

- **Trades**: Complete trade history with entry/exit details
- **Positions**: Current open positions synchronized with exchange
- **Diary Entries**: AI decision log including HOLD actions
- **Bot State**: Historical snapshots for performance tracking
- **Trade Proposals**: Manual mode trade recommendations
- **Market Data**: OHLCV and indicator snapshots (future)

## Database Schema

### Tables

#### `trades`
Complete trade records with entry/exit details, P&L, and AI reasoning.

**Key Fields:**
- `asset`, `action` (buy/sell)
- Entry: `entry_timestamp`, `entry_price`, `entry_size`, `entry_value`
- Exit: `exit_timestamp`, `exit_price`, `exit_value`
- P&L: `realized_pnl`, `realized_pnl_pct`
- Risk: `leverage`, `stop_loss`, `take_profit`
- AI: `llm_model`, `rationale`, `reasoning_tokens`
- Status: `open`, `closed`, `cancelled`

#### `positions`
Current open positions with real-time P&L.

**Key Fields:**
- `asset`, `side` (long/short)
- `size`, `entry_price`, `current_price`, `liquidation_price`
- `unrealized_pnl`, `unrealized_pnl_pct`
- `leverage`, `margin`
- `trade_id` (FK to trades)

#### `diary_entries`
AI decision log - all decisions including HOLD.

**Key Fields:**
- `timestamp`, `asset`, `action` (hold/buy/sell)
- `rationale` (LLM reasoning)
- `price`, `indicators` (JSON snapshot)
- `trade_id` (FK if action resulted in trade)

#### `bot_states`
Periodic snapshots of bot state for equity curve and analytics.

**Key Fields:**
- `timestamp`
- Account: `balance`, `total_value`, `equity`
- Performance: `total_return_pct`, `sharpe_ratio`, `win_rate`
- Positions: `open_positions_count`, `total_position_value`, `total_unrealized_pnl`
- Trades: `total_trades`, `winning_trades`, `losing_trades`
- Risk: `max_drawdown`, `avg_profit`, `avg_loss`, `profit_factor`

#### `trade_proposals`
Manual mode: AI trade recommendations awaiting approval.

**Key Fields:**
- `asset`, `action`, `size`, `price`
- `rationale`, `confidence`
- `stop_loss`, `take_profit`, `leverage`
- Status: `pending`, `approved`, `rejected`, `executed`, `failed`, `expired`
- `reviewed_at`, `rejection_reason`
- `execution_price`, `trade_id` (FK)

#### `market_data` (optional)
Historical market data for backtesting (future feature).

**Key Fields:**
- `asset`, `timestamp`, `interval`
- OHLCV: `open`, `high`, `low`, `close`, `volume`
- `open_interest`, `funding_rate`
- `indicators` (JSON of all technical indicators)

## Usage

### Basic Usage

```python
from src.database.db_manager import get_db_manager

# Get database manager (singleton)
db = get_db_manager()

# Create a trade
trade = db.create_trade(
    asset='BTC',
    action='buy',
    entry_price=45000.0,
    entry_size=0.1,
    entry_value=4500.0,
    leverage=2.0,
    stop_loss=44000.0,
    take_profit=46000.0,
    llm_model='x-ai/grok-4',
    rationale='Strong bullish momentum...',
)

# Close the trade
db.close_trade(
    trade_id=trade.id,
    exit_price=46200.0,
    exit_value=4620.0,
    realized_pnl=120.0,
    realized_pnl_pct=2.67,
)

# Save bot state snapshot
db.save_bot_state(
    balance=10120.0,
    total_value=10120.0,
    equity=10120.0,
    total_return_pct=1.2,
    sharpe_ratio=1.45,
)

# Query trades
recent_trades = db.get_trades(asset='BTC', limit=10)
open_trades = db.get_open_trades()
stats = db.get_trade_stats()

# Diary entries
db.create_diary_entry(
    asset='ETH',
    action='hold',
    rationale='Waiting for confirmation...',
    price=3200.0,
)

recent_diary = db.get_recent_diary(limit=10)

# Trade proposals (manual mode)
proposal = db.create_trade_proposal(
    asset='SOL',
    action='buy',
    size=10.0,
    price=150.0,
    rationale='Breakout confirmation...',
    confidence=0.85,
)

db.approve_proposal(proposal.id)
```

### Migration from JSONL

To migrate existing `data/diary.jsonl` to database:

```bash
python scripts/migrate_to_database.py
```

This will:
1. Create SQLite database at `data/bot.db`
2. Import all diary entries from JSONL
3. Backup original file to `diary.jsonl.backup`

## Database Location

Default: `data/bot.db` (SQLite)

Can be customized via connection string:

```python
db = DatabaseManager(db_url='sqlite:///custom/path/bot.db')
```

For PostgreSQL (future):
```python
db = DatabaseManager(db_url='postgresql://user:pass@host:5432/trading_bot')
```

## Integration with Bot Engine

The bot engine will be updated to use the database instead of JSONL:

**Before (JSONL):**
```python
# Append to diary.jsonl
with open('data/diary.jsonl', 'a') as f:
    f.write(json.dumps(entry) + '\n')
```

**After (Database):**
```python
# Save to database
db.create_diary_entry(
    asset=asset,
    action=action,
    rationale=rationale,
    price=price,
)
```

## Performance

- **Indexing**: Optimized indexes on common query patterns
  - `asset + timestamp` for time-series queries
  - `status + timestamp` for filtering
  - `trade_id` foreign keys

- **Session Management**: Automatic session handling via context managers

- **Connection Pooling**: SQLAlchemy pool for concurrent access

## Maintenance

### Database Stats

```python
stats = db.get_database_stats()
print(stats)
# {
#   'trades': 245,
#   'open_trades': 3,
#   'closed_trades': 242,
#   'positions': 3,
#   'diary_entries': 1523,
#   'bot_states': 187,
#   'trade_proposals': 12,
#   'pending_proposals': 2,
# }
```

### Backup

SQLite database can be backed up by copying `data/bot.db`:

```bash
cp data/bot.db data/bot_backup_$(date +%Y%m%d).db
```

### Reset Database

⚠️ **CAUTION**: This deletes all data!

```python
from src.database.models import drop_tables, create_tables
from src.database.db_manager import get_db_manager

db = get_db_manager()
drop_tables(db.engine)
create_tables(db.engine)
```

## Future Enhancements

- [ ] Automatic bot state snapshots (every 5 minutes)
- [ ] Market data collection for backtesting
- [ ] Trade performance analytics dashboard
- [ ] Database migration utilities (Alembic)
- [ ] PostgreSQL support for production
- [ ] Sharding for large-scale data
- [ ] Data export/import utilities
- [ ] Historical trade replay

## Files

- `models.py` - SQLAlchemy model definitions
- `db_manager.py` - High-level database interface
- `README.md` - This file
- `../scripts/migrate_to_database.py` - JSONL migration script

## Dependencies

- `sqlalchemy>=2.0.0` - ORM framework
- `sqlite3` - Included with Python (default backend)

## Migration Status

✅ **COMPLETED**
- Database schema designed
- Models implemented
- Database manager with full CRUD operations
- Migration script from JSONL
- 26 diary entries migrated successfully

⏳ **PENDING**
- Integration with bot_engine.py (replace JSONL writes)
- Integration with bot_service.py (query database for GUI)
- Automatic bot state snapshots
- Trade creation/closing hooks

## Notes

- Database uses UTC timestamps consistently
- All monetary values in USD
- Leverage represented as decimal (2.0 = 2x)
- Foreign key constraints enabled
- Cascade deletes NOT enabled (safety)
