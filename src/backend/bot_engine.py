"""
Trading Bot Engine - Core trading logic separated from UI
Refactored from ai-trading-agent/src/main.py
"""

import asyncio
import json
import logging
from collections import deque, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

from src.backend.agent.decision_maker import TradingAgent
from src.backend.config_loader import CONFIG
from src.backend.indicators.taapi_client import TAAPIClient
from src.backend.models.trade_proposal import TradeProposal
from src.backend.trading.hyperliquid_api import HyperliquidAPI
from src.backend.utils.prompt_utils import json_default


@dataclass
class BotState:
    """Bot state for UI updates"""
    is_running: bool = False
    balance: float = 0.0
    total_value: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    positions: List[Dict] = field(default_factory=list)
    active_trades: List[Dict] = field(default_factory=list)
    open_orders: List[Dict] = field(default_factory=list)
    recent_fills: List[Dict] = field(default_factory=list)
    market_data: List[Dict] = field(default_factory=list)  # Market data for dashboard
    pending_proposals: List[Dict] = field(default_factory=list)  # Pending trade proposals (manual mode)
    last_reasoning: Dict = field(default_factory=dict)
    last_update: str = ""
    error: Optional[str] = None
    invocation_count: int = 0


class TradingBotEngine:
    """
    Core trading bot engine independent of UI.
    Communicates with GUI via callback system.
    """

    def __init__(
        self,
        assets: List[str],
        interval: str,
        on_state_update: Optional[Callable[[BotState], None]] = None,
        on_trade_executed: Optional[Callable[[Dict], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize trading bot engine.

        Args:
            assets: List of trading assets (e.g., ["BTC", "ETH"])
            interval: Trading interval (e.g., "5m", "1h")
            on_state_update: Callback for state updates
            on_trade_executed: Callback when trade is executed
            on_error: Callback for errors
        """
        self.assets = assets
        self.interval = interval
        self.on_state_update = on_state_update
        self.on_trade_executed = on_trade_executed
        self.on_error = on_error

        # Logging (initialize first!)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("bot.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Initialize trading components
        self.taapi = TAAPIClient()
        self.hyperliquid = HyperliquidAPI()
        self.agent = TradingAgent()

        # Bot state
        self.state = BotState()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

        # Internal state tracking (from original main.py)
        self.start_time: Optional[datetime] = None
        self.invocation_count = 0
        self.trade_log: List[float] = []  # For Sharpe calculation
        self.active_trades: List[Dict] = []  # Local tracking of open positions
        self.recent_events: deque = deque(maxlen=200)
        self.initial_account_value: Optional[float] = None
        self.price_history: Dict[str, deque] = {asset: deque(maxlen=60) for asset in assets}
        
        # Manual trading mode
        self.trading_mode = CONFIG.get("trading_mode", "auto").lower()
        self.pending_proposals: List[TradeProposal] = []
        self.logger.info(f"Trading mode: {self.trading_mode.upper()}")

        # File paths
        self.diary_path = Path("data/diary.jsonl")
        self.diary_path.parent.mkdir(parents=True, exist_ok=True)

    async def start(self):
        """Start the trading bot"""
        if self.is_running:
            self.logger.warning("Bot already running")
            return

        self.is_running = True
        self.state.is_running = True
        self.start_time = datetime.now(UTC)
        self.invocation_count = 0

        # Get initial account value
        try:
            user_state = await self.hyperliquid.get_user_state()
            self.initial_account_value = user_state.get('total_value', 0.0)
            if self.initial_account_value == 0.0:
                self.initial_account_value = user_state.get('balance', 10000.0)
        except Exception as e:
            self.logger.error(f"Failed to get initial account value: {e}")
            self.initial_account_value = 10000.0

        self._task = asyncio.create_task(self._main_loop())
        self.logger.info(f"Bot started - Assets: {self.assets}, Interval: {self.interval}")
        self._notify_state_update()

    async def stop(self):
        """Stop the trading bot"""
        if not self.is_running:
            return

        self.is_running = False
        self.state.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.logger.info("Bot stopped")
        self._notify_state_update()

    async def _main_loop(self):
        """
        Main trading loop.
        Adapted from ai-trading-agent/src/main.py lines 88-455
        """
        try:
            while self.is_running:
                self.invocation_count += 1
                self.state.invocation_count = self.invocation_count

                try:
                    # ===== PHASE 1: Fetch Account State =====
                    state = await self.hyperliquid.get_user_state()
                    balance = state['balance']
                    total_value = state['total_value']

                    # Calculate total return
                    initial_balance = 10000.0  # TODO: load from config
                    total_return_pct = ((total_value - initial_balance) / initial_balance) * 100

                    sharpe_ratio = self._calculate_sharpe(self.trade_log)
                    
                    self.logger.debug(f"  Balance: ${balance:,.2f} | Return: {total_return_pct:+.2f}% | Sharpe: {sharpe_ratio:.2f}")

                    # Update bot state
                    self.state.balance = balance
                    self.state.total_value = total_value
                    self.state.total_return_pct = total_return_pct
                    self.state.sharpe_ratio = sharpe_ratio

                    # ===== PHASE 2: Enrich Positions =====
                    enriched_positions = []
                    for pos in state['positions']:
                        symbol = pos.get('coin')
                        try:
                            current_price = await self.hyperliquid.get_current_price(symbol)
                            enriched_positions.append({
                                'symbol': symbol,
                                'quantity': float(pos.get('szi', 0) or 0),
                                'entry_price': float(pos.get('entryPx', 0) or 0),
                                'current_price': current_price,
                                'liquidation_price': float(pos.get('liquidationPx', 0) or 0),
                                'unrealized_pnl': pos.get('pnl', 0.0),
                                'leverage': pos.get('leverage', {}).get('value', 1) if isinstance(pos.get('leverage'), dict) else pos.get('leverage', 1)
                            })
                        except Exception as e:
                            self.logger.error(f"Error enriching position for {symbol}: {e}")

                    self.state.positions = enriched_positions

                    # ===== PHASE 3: Load Recent Diary =====
                    recent_diary = self._load_recent_diary(limit=10)

                    # ===== PHASE 4: Fetch Open Orders =====
                    open_orders_raw = await self.hyperliquid.get_open_orders()
                    open_orders = []
                    for o in open_orders_raw:
                        order_type_obj = o.get('orderType', {})
                        trigger_price = None
                        order_type_str = 'limit'

                        if isinstance(order_type_obj, dict) and 'trigger' in order_type_obj:
                            order_type_str = 'trigger'
                            trigger_data = order_type_obj.get('trigger', {})
                            if 'triggerPx' in trigger_data:
                                trigger_price = float(trigger_data['triggerPx'])

                        open_orders.append({
                            'coin': o.get('coin'),
                            'oid': o.get('oid'),
                            'is_buy': o.get('side') == 'B',
                            'size': float(o.get('sz', 0)),
                            'price': float(o.get('limitPx', 0)),
                            'trigger_price': trigger_price,
                            'order_type': order_type_str
                        })

                    self.state.open_orders = open_orders

                    # ===== PHASE 5: Reconcile Active Trades =====
                    await self._reconcile_active_trades(state['positions'], open_orders_raw)

                    # ===== PHASE 6: Fetch Recent Fills =====
                    fills_raw = await self.hyperliquid.get_recent_fills(limit=50)
                    recent_fills = []
                    for fill in fills_raw[-20:]:
                        ts = fill.get('time')
                        if ts and ts > 1_000_000_000_000:
                            ts = ts / 1000
                        ts_str = datetime.fromtimestamp(ts, UTC).isoformat() if ts else ""

                        recent_fills.append({
                            'timestamp': ts_str,
                            'coin': fill.get('coin'),
                            'is_buy': fill.get('side') == 'B',
                            'size': float(fill.get('sz', 0)),
                            'price': float(fill.get('px', 0))
                        })

                    self.state.recent_fills = recent_fills

                    # ===== PHASE 7: Build Dashboard =====
                    dashboard = {
                        'total_return_pct': total_return_pct,
                        'balance': balance,
                        'account_value': total_value,
                        'sharpe_ratio': sharpe_ratio,
                        'positions': enriched_positions,
                        'active_trades': self.active_trades,
                        'open_orders': open_orders,
                        'recent_diary': recent_diary,
                        'recent_fills': recent_fills
                    }

                    # ===== PHASE 8: Gather Market Data =====
                    market_sections = []
                    for idx, asset in enumerate(self.assets):
                        try:
                            # Current price
                            current_price = await self.hyperliquid.get_current_price(asset)

                            # Store price history
                            self.price_history[asset].append({
                                't': datetime.now(UTC).isoformat(),
                                'mid': current_price
                            })

                            # Open interest and funding
                            oi = await self.hyperliquid.get_open_interest(asset)
                            funding = await self.hyperliquid.get_funding_rate(asset)

                            # Fetch all indicators using bulk endpoint (2 requests instead of 10)
                            # Note: fetch_asset_indicators() already includes 15s delay between 5m and interval requests
                            # Uses caching to avoid redundant API calls
                            indicators = self.taapi.fetch_asset_indicators(asset)
                            
                            # Add delay between assets to respect TAAPI rate limit (1 req/15s)
                            # Only wait if this is not the last asset
                            if idx < len(self.assets) - 1:
                                self.logger.info(f"Waiting 15s before fetching next asset (TAAPI rate limit)...")
                                await asyncio.sleep(15)
                            
                            # Extract 5m indicators
                            ema20_5m_series = indicators["5m"].get("ema20", [])
                            macd_5m_series = indicators["5m"].get("macd", [])
                            rsi7_5m_series = indicators["5m"].get("rsi7", [])
                            rsi14_5m_series = indicators["5m"].get("rsi14", [])

                            # Extract long-term indicators (interval from config: 1h, 4h, etc.)
                            interval = CONFIG.get("interval", "1h")
                            lt_indicators = indicators.get(interval, {})
                            lt_ema20 = lt_indicators.get("ema20")
                            lt_ema50 = lt_indicators.get("ema50")
                            lt_atr3 = lt_indicators.get("atr3")
                            lt_atr14 = lt_indicators.get("atr14")
                            lt_macd_series = lt_indicators.get("macd", [])
                            lt_rsi_series = lt_indicators.get("rsi14", [])

                            # Build market data structure
                            market_sections.append({
                                "asset": asset,
                                "current_price": current_price,
                                "intraday": {
                                    "ema20": ema20_5m_series[-1] if ema20_5m_series else None,
                                    "macd": macd_5m_series[-1] if macd_5m_series else None,
                                    "rsi7": rsi7_5m_series[-1] if rsi7_5m_series else None,
                                    "rsi14": rsi14_5m_series[-1] if rsi14_5m_series else None,
                                    "series": {
                                        "ema20": ema20_5m_series,
                                        "macd": macd_5m_series,
                                        "rsi7": rsi7_5m_series,
                                        "rsi14": rsi14_5m_series
                                    }
                                },
                                "long_term": {
                                    "ema20": lt_ema20,
                                    "ema50": lt_ema50,
                                    "atr3": lt_atr3,
                                    "atr14": lt_atr14,
                                    "macd_series": lt_macd_series,
                                    "rsi_series": lt_rsi_series
                                },
                                "open_interest": oi,
                                "funding_rate": funding,
                                "funding_annualized_pct": funding * 24 * 365 * 100 if funding else None,
                                "recent_mid_prices": [p['mid'] for p in list(self.price_history[asset])[-10:]]
                            })

                        except Exception as e:
                            self.logger.error(f"Error gathering market data for {asset}: {e}")

                    # ===== PHASE 9: Build LLM Context =====
                    context_payload = OrderedDict([
                        ("invocation", {
                            "count": self.invocation_count,
                            "current_time": datetime.now(UTC).isoformat()
                        }),
                        ("account", dashboard),
                        ("market_data", market_sections),
                        ("instructions", {
                            "assets": self.assets,
                            "note": "Follow the system prompt guidelines strictly"
                        })
                    ])
                    context = json.dumps(context_payload, default=json_default, indent=2)

                    # Log prompt
                    with open("data/prompts.log", "a", encoding="utf-8") as f:
                        f.write(f"\n{'='*80}\n")
                        f.write(f"Invocation {self.invocation_count} - {datetime.now(UTC).isoformat()}\n")
                        f.write(f"{'='*80}\n")
                        f.write(context + "\n")

                    # ===== PHASE 10: Get LLM Decision =====
                    decisions = await asyncio.to_thread(
                        self.agent.decide_trade, self.assets, context
                    )

                    # Validate and retry if needed
                    if not isinstance(decisions, dict) or 'trade_decisions' not in decisions:
                        self.logger.warning("Invalid decision format, retrying with strict prefix...")
                        strict_context = (
                            "Return ONLY the JSON object per the schema. "
                            "No markdown, no explanation.\n\n" + context
                        )
                        decisions = await asyncio.to_thread(
                            self.agent.decide_trade, self.assets, strict_context
                        )

                    # Check for all-hold with parse errors
                    trade_decisions = decisions.get('trade_decisions', [])
                    if all(
                        d.get('action') == 'hold' and 'parse error' in d.get('rationale', '').lower()
                        for d in trade_decisions
                    ):
                        self.logger.warning("All holds with parse errors, retrying...")
                        decisions = await asyncio.to_thread(
                            self.agent.decide_trade, self.assets, context
                        )
                        trade_decisions = decisions.get('trade_decisions', [])

                    # Extract reasoning
                    reasoning = decisions.get('reasoning', '')
                    if reasoning:
                        self.logger.info(f"LLM Reasoning: {reasoning[:200]}...")

                    self.state.last_reasoning = decisions

                    # ===== PHASE 11: Execute Trades or Create Proposals =====
                    for decision in trade_decisions:
                        asset = decision.get('asset')
                        if asset not in self.assets:
                            continue

                        action = decision.get('action')
                        rationale = decision.get('rationale', '')
                        allocation = float(decision.get('allocation_usd', 0))
                        tp_price = decision.get('tp_price')
                        sl_price = decision.get('sl_price')
                        exit_plan = decision.get('exit_plan', '')
                        confidence = decision.get('confidence', 75.0)

                        if action in ['buy', 'sell']:
                            # MANUAL MODE: Create proposal instead of executing
                            if self.trading_mode == "manual":
                                try:
                                    current_price = await self.hyperliquid.get_current_price(asset)
                                    size = allocation / current_price if current_price > 0 else 0
                                    
                                    # Calculate risk/reward
                                    risk_reward = None
                                    if tp_price and sl_price and current_price:
                                        potential_gain = abs(tp_price - current_price) / current_price
                                        potential_loss = abs(sl_price - current_price) / current_price
                                        if potential_loss > 0:
                                            risk_reward = potential_gain / potential_loss
                                    
                                    proposal = TradeProposal(
                                        asset=asset,
                                        action=action,
                                        confidence=confidence,
                                        risk_reward=risk_reward,
                                        entry_price=current_price,
                                        tp_price=tp_price,
                                        sl_price=sl_price,
                                        size=size,
                                        allocation=allocation,
                                        rationale=rationale,
                                        market_conditions={
                                            'current_price': current_price,
                                            'exit_plan': exit_plan
                                        }
                                    )
                                    
                                    self.pending_proposals.append(proposal)
                                    self.logger.info(f"[PROPOSAL] Created: {action.upper()} {asset} @ ${current_price:,.2f} (ID: {proposal.id[:8]})")
                                    
                                    # Update state with proposals
                                    self.state.pending_proposals = [p.to_dict() for p in self.pending_proposals if p.is_pending]
                                    
                                except Exception as e:
                                    self.logger.error(f"Error creating proposal for {asset}: {e}")
                                    
                                continue  # Skip execution in manual mode
                            
                            # AUTO MODE: Execute immediately (original behavior)
                            try:
                                current_price = await self.hyperliquid.get_current_price(asset)
                                amount = allocation / current_price if current_price > 0 else 0

                                if amount > 0:
                                    # Place market order
                                    if action == 'buy':
                                        order_result = await self.hyperliquid.place_buy_order(asset, amount)
                                    else:
                                        order_result = await self.hyperliquid.place_sell_order(asset, amount)

                                    self.logger.info(f"Executed {action} {asset}: {amount:.6f} @ {current_price}")

                                    # Wait and check fills
                                    await asyncio.sleep(1)
                                    recent_fills_check = await self.hyperliquid.get_recent_fills(limit=5)
                                    filled = any(
                                        f.get('coin') == asset and
                                        abs(float(f.get('sz', 0)) - amount) < 0.0001
                                        for f in recent_fills_check
                                    )

                                    # Place TP/SL orders
                                    tp_oid = None
                                    sl_oid = None

                                    if tp_price:
                                        try:
                                            is_buy = (action == 'buy')
                                            tp_order = await self.hyperliquid.place_take_profit(
                                                asset, is_buy, amount, tp_price
                                            )
                                            oids = self.hyperliquid.extract_oids(tp_order)
                                            tp_oid = oids[0] if oids else None
                                            self.logger.info(f"Placed TP order for {asset} @ {tp_price}")
                                        except Exception as e:
                                            self.logger.error(f"Failed to place TP: {e}")

                                    if sl_price:
                                        try:
                                            is_buy = (action == 'buy')
                                            sl_order = await self.hyperliquid.place_stop_loss(
                                                asset, is_buy, amount, sl_price
                                            )
                                            oids = self.hyperliquid.extract_oids(sl_order)
                                            sl_oid = oids[0] if oids else None
                                            self.logger.info(f"Placed SL order for {asset} @ {sl_price}")
                                        except Exception as e:
                                            self.logger.error(f"Failed to place SL: {e}")

                                    # Update active trades
                                    self.active_trades = [
                                        t for t in self.active_trades if t['asset'] != asset
                                    ]
                                    self.active_trades.append({
                                        'asset': asset,
                                        'is_long': (action == 'buy'),
                                        'amount': amount,
                                        'entry_price': current_price,
                                        'tp_oid': tp_oid,
                                        'sl_oid': sl_oid,
                                        'exit_plan': exit_plan,
                                        'opened_at': datetime.now(UTC).isoformat()
                                    })

                                    # Write to diary
                                    self._write_diary_entry({
                                        'timestamp': datetime.now(UTC).isoformat(),
                                        'asset': asset,
                                        'action': action,
                                        'allocation_usd': allocation,
                                        'amount': amount,
                                        'entry_price': current_price,
                                        'tp_price': tp_price,
                                        'tp_oid': tp_oid,
                                        'sl_price': sl_price,
                                        'sl_oid': sl_oid,
                                        'exit_plan': exit_plan,
                                        'rationale': rationale,
                                        'order_result': str(order_result),
                                        'opened_at': datetime.now(UTC).isoformat(),
                                        'filled': filled
                                    })

                                    # Notify GUI of trade
                                    if self.on_trade_executed:
                                        self.on_trade_executed({
                                            'asset': asset,
                                            'action': action,
                                            'amount': amount,
                                            'price': current_price,
                                            'timestamp': datetime.now(UTC).isoformat()
                                        })

                                    # Track PnL for Sharpe
                                    # (Simplified - actual PnL tracked on position close)

                            except Exception as e:
                                self.logger.error(f"Error executing {action} for {asset}: {e}")
                                if self.on_error:
                                    self.on_error(f"Trade execution error: {e}")

                        elif action == 'hold':
                            self.logger.info(f"{asset}: HOLD - {rationale}")
                            self._write_diary_entry({
                                'timestamp': datetime.now(UTC).isoformat(),
                                'asset': asset,
                                'action': 'hold',
                                'rationale': rationale
                            })

                    # Update market data in state for dashboard
                    self.state.market_data = market_sections
                    
                    # Update state timestamp
                    self.state.last_update = datetime.now(UTC).isoformat()
                    self._notify_state_update()

                except Exception as e:
                    self.logger.error(f"Error in main loop iteration: {e}", exc_info=True)
                    self.state.error = str(e)
                    if self.on_error:
                        self.on_error(str(e))

                # ===== PHASE 12: Sleep Until Next Interval =====
                await asyncio.sleep(self._get_interval_seconds())

        except asyncio.CancelledError:
            self.logger.info("Bot loop cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in bot loop: {e}", exc_info=True)
            self.state.error = str(e)
            if self.on_error:
                self.on_error(str(e))

    async def _reconcile_active_trades(self, positions: List[Dict], open_orders: List[Dict]):
        """
        Reconcile local active_trades with exchange state.
        Remove stale entries that no longer exist on exchange.
        """
        exchange_assets = {pos.get('coin') for pos in positions}
        order_assets = {o.get('coin') for o in open_orders}
        tracked_assets = exchange_assets | order_assets

        removed = []
        for trade in self.active_trades[:]:
            if trade['asset'] not in tracked_assets:
                self.active_trades.remove(trade)
                removed.append(trade['asset'])

        if removed:
            self.logger.info(f"Reconciled: removed stale trades for {removed}")
            self._write_diary_entry({
                'timestamp': datetime.now(UTC).isoformat(),
                'action': 'reconcile',
                'removed_assets': removed,
                'note': 'Position no longer exists on exchange'
            })

    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate naive Sharpe ratio from returns list"""
        if len(returns) < 2:
            return 0.0

        try:
            import statistics
            mean = statistics.mean(returns)
            stdev = statistics.stdev(returns)
            return mean / stdev if stdev > 0 else 0.0
        except Exception:
            return 0.0

    def _get_interval_seconds(self) -> int:
        """Convert interval string to seconds"""
        if self.interval.endswith('m'):
            return int(self.interval[:-1]) * 60
        elif self.interval.endswith('h'):
            return int(self.interval[:-1]) * 3600
        elif self.interval.endswith('d'):
            return int(self.interval[:-1]) * 86400
        return 300  # default 5 minutes

    def _notify_state_update(self):
        """Notify GUI of state update via callback"""
        if self.on_state_update:
            try:
                self.on_state_update(self.state)
            except Exception as e:
                self.logger.error(f"Error in state update callback: {e}")

    def _write_diary_entry(self, entry: Dict):
        """Write entry to diary.jsonl"""
        try:
            with open(self.diary_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=json_default) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write diary entry: {e}")

    def _load_recent_diary(self, limit: int = 10) -> List[Dict]:
        """Load recent diary entries"""
        if not self.diary_path.exists():
            return []

        try:
            entries = []
            with open(self.diary_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return entries[-limit:]
        except Exception as e:
            self.logger.error(f"Failed to load diary: {e}")
            return []

    def get_state(self) -> BotState:
        """Get current bot state"""
        return self.state

    def get_assets(self) -> List[str]:
        """Get configured assets"""
        return self.assets

    def get_interval(self) -> str:
        """Get configured interval"""
        return self.interval

    async def close_position(self, asset: str) -> bool:
        """
        Manually close a position for given asset.

        Args:
            asset: Asset symbol to close

        Returns:
            True if successful, False otherwise
        """
        try:
            # Cancel all orders for this asset
            await self.hyperliquid.cancel_all_orders(asset)

            # Find position
            for pos in self.state.positions:
                if pos['symbol'] == asset:
                    quantity = abs(pos['quantity'])
                    if quantity > 0:
                        # Close position (reverse direction)
                        if pos['quantity'] > 0:  # Long position
                            await self.hyperliquid.place_sell_order(asset, quantity)
                        else:  # Short position
                            await self.hyperliquid.place_buy_order(asset, quantity)

                        # Remove from active trades
                        self.active_trades = [
                            t for t in self.active_trades if t['asset'] != asset
                        ]

                        self._write_diary_entry({
                            'timestamp': datetime.now(UTC).isoformat(),
                            'asset': asset,
                            'action': 'manual_close',
                            'quantity': quantity,
                            'note': 'Position closed manually via GUI'
                        })

                        self.logger.info(f"Manually closed position: {asset}")
                        return True

            self.logger.warning(f"No position found to close: {asset}")
            return False

        except Exception as e:
            self.logger.error(f"Failed to close position {asset}: {e}")
            if self.on_error:
                self.on_error(f"Failed to close position: {e}")
            return False
    
    # ===== MANUAL TRADING MODE METHODS =====
    
    def get_pending_proposals(self) -> List[TradeProposal]:
        """Get list of pending trade proposals"""
        return [p for p in self.pending_proposals if p.is_pending]
    
    def approve_proposal(self, proposal_id: str) -> bool:
        """
        Approve and execute a trade proposal.
        
        Args:
            proposal_id: ID of the proposal to approve
            
        Returns:
            True if proposal found and approved, False otherwise
        """
        proposal = next((p for p in self.pending_proposals if p.id == proposal_id), None)
        
        if not proposal or not proposal.is_pending:
            self.logger.warning(f"Proposal {proposal_id} not found or not pending")
            return False
        
        # Mark as approved
        proposal.approve()
        self.logger.info(f"[APPROVED] Proposal: {proposal.action.upper()} {proposal.asset} (ID: {proposal_id[:8]})")
        
        # Execute asynchronously
        asyncio.create_task(self._execute_proposal(proposal))
        
        # Update state
        self.state.pending_proposals = [p.to_dict() for p in self.pending_proposals if p.is_pending]
        self._notify_state_update()
        
        return True
    
    def reject_proposal(self, proposal_id: str, reason: Optional[str] = None) -> bool:
        """
        Reject a trade proposal.
        
        Args:
            proposal_id: ID of the proposal to reject
            reason: Optional reason for rejection
            
        Returns:
            True if proposal found and rejected, False otherwise
        """
        proposal = next((p for p in self.pending_proposals if p.id == proposal_id), None)
        
        if not proposal or not proposal.is_pending:
            self.logger.warning(f"Proposal {proposal_id} not found or not pending")
            return False
        
        # Mark as rejected
        proposal.reject(reason or "Rejected by user")
        self.logger.info(f"[REJECTED] Proposal: {proposal.action.upper()} {proposal.asset} (ID: {proposal_id[:8]})")
        
        # Write to diary
        self._write_diary_entry({
            'timestamp': datetime.now(UTC).isoformat(),
            'asset': proposal.asset,
            'action': 'proposal_rejected',
            'proposal_id': proposal_id,
            'reason': reason,
            'rationale': proposal.rationale
        })
        
        # Update state
        self.state.pending_proposals = [p.to_dict() for p in self.pending_proposals if p.is_pending]
        self._notify_state_update()
        
        return True
    
    async def _execute_proposal(self, proposal: TradeProposal):
        """
        Execute an approved trade proposal.
        
        Args:
            proposal: The approved proposal to execute
        """
        try:
            self.logger.info(f"Executing proposal: {proposal.action.upper()} {proposal.asset}")
            
            # Get fresh price
            current_price = await self.hyperliquid.get_current_price(proposal.asset)
            amount = proposal.size
            
            if amount <= 0:
                raise ValueError(f"Invalid amount: {amount}")
            
            # Place market order
            if proposal.action == 'buy':
                order_result = await self.hyperliquid.place_buy_order(proposal.asset, amount)
            elif proposal.action == 'sell':
                order_result = await self.hyperliquid.place_sell_order(proposal.asset, amount)
            else:
                raise ValueError(f"Invalid action: {proposal.action}")
            
            self.logger.info(f"Order placed: {proposal.action} {proposal.asset}: {amount:.6f} @ {current_price}")
            
            # Wait and check fills
            await asyncio.sleep(1)
            recent_fills = await self.hyperliquid.get_recent_fills(limit=5)
            filled = any(
                f.get('coin') == proposal.asset and
                abs(float(f.get('sz', 0)) - amount) < 0.0001
                for f in recent_fills
            )
            
            # Place TP/SL if specified
            tp_oid = None
            sl_oid = None
            
            if proposal.tp_price:
                try:
                    is_buy = (proposal.action == 'buy')
                    tp_order = await self.hyperliquid.place_take_profit(
                        proposal.asset, is_buy, amount, proposal.tp_price
                    )
                    oids = self.hyperliquid.extract_oids(tp_order)
                    tp_oid = oids[0] if oids else None
                    self.logger.info(f"Placed TP order @ {proposal.tp_price}")
                except Exception as e:
                    self.logger.error(f"Failed to place TP: {e}")
            
            if proposal.sl_price:
                try:
                    is_buy = (proposal.action == 'buy')
                    sl_order = await self.hyperliquid.place_stop_loss(
                        proposal.asset, is_buy, amount, proposal.sl_price
                    )
                    oids = self.hyperliquid.extract_oids(sl_order)
                    sl_oid = oids[0] if oids else None
                    self.logger.info(f"Placed SL order @ {proposal.sl_price}")
                except Exception as e:
                    self.logger.error(f"Failed to place SL: {e}")
            
            # Update active trades
            self.active_trades = [
                t for t in self.active_trades if t['asset'] != proposal.asset
            ]
            self.active_trades.append({
                'asset': proposal.asset,
                'is_long': (proposal.action == 'buy'),
                'amount': amount,
                'entry_price': current_price,
                'tp_oid': tp_oid,
                'sl_oid': sl_oid,
                'exit_plan': proposal.market_conditions.get('exit_plan', ''),
                'opened_at': datetime.now(UTC).isoformat(),
                'from_proposal': proposal.id
            })
            
            # Mark proposal as executed
            proposal.mark_executed(current_price)
            
            # Write to diary
            self._write_diary_entry({
                'timestamp': datetime.now(UTC).isoformat(),
                'asset': proposal.asset,
                'action': proposal.action,
                'allocation_usd': proposal.allocation,
                'amount': amount,
                'entry_price': current_price,
                'tp_price': proposal.tp_price,
                'tp_oid': tp_oid,
                'sl_price': proposal.sl_price,
                'sl_oid': sl_oid,
                'rationale': proposal.rationale,
                'order_result': str(order_result),
                'filled': filled,
                'from_proposal': proposal.id,
                'approved_manually': True
            })
            
            # Notify GUI
            if self.on_trade_executed:
                self.on_trade_executed({
                    'asset': proposal.asset,
                    'action': proposal.action,
                    'amount': amount,
                    'price': current_price,
                    'timestamp': datetime.now(UTC).isoformat(),
                    'from_proposal': True
                })
            
            self.logger.info(f"[SUCCESS] Proposal executed: {proposal.id[:8]}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute proposal {proposal.id}: {e}")
            proposal.mark_failed(str(e))
            
            if self.on_error:
                self.on_error(f"Failed to execute trade: {e}")
        
        finally:
            # Update state
            self.state.pending_proposals = [p.to_dict() for p in self.pending_proposals if p.is_pending]
            self._notify_state_update()
