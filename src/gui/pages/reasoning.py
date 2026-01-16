"""
Reasoning Page - AI decision visualization with JSON editor and timeline
"""

import json
import asyncio
from datetime import datetime
from nicegui import ui
from src.gui.services.bot_service import BotService
from src.gui.services.state_manager import StateManager


def create_reasoning(bot_service: BotService, state_manager: StateManager):
    """Create AI reasoning page with JSON editor and decision timeline"""

    ui.label('AI Reasoning').classes('text-3xl font-bold mb-4 text-white')

    # ===== JSON EDITOR SECTION =====
    with ui.card().classes('w-full p-4 mb-6'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('LLM Raw Output').classes('text-xl font-bold text-white')

            with ui.row().classes('gap-2'):
                # Copy to clipboard button
                async def copy_json():
                    state = state_manager.get_state()
                    reasoning_data = state.last_reasoning or {}
                    json_str = json.dumps(reasoning_data, indent=2)
                    ui.clipboard.write(json_str)
                    ui.notify('JSON copied to clipboard!', type='positive')

                ui.button('📋 Copy JSON', on_click=copy_json).props('size=sm')

                # Export as file button
                async def export_json():
                    state = state_manager.get_state()
                    reasoning_data = state.last_reasoning or {}
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'reasoning_{timestamp}.json'
                    json_str = json.dumps(reasoning_data, indent=2)

                    # Create download link
                    ui.download(json_str, filename)
                    ui.notify(f'Exporting {filename}...', type='info')

                ui.button('⬇️ Export JSON', on_click=export_json).props('size=sm')

        # JSON editor with read-only mode
        json_editor = ui.json_editor({
            'content': {'json': {}},
            'mode': 'tree',
            'mainMenuBar': False,
            'navigationBar': False,
            'readOnly': True
        }).classes('w-full h-96')

    # ===== TIMELINE FILTERS =====
    with ui.card().classes('w-full p-4 mb-6'):
        with ui.row().classes('w-full items-center gap-4'):
            ui.label('Filter Decisions:').classes('text-sm font-bold text-white')

            action_filter = ui.select(
                label='',
                value='all',
                options={'all': 'All Actions', 'buy': 'Buy Only', 'sell': 'Sell Only', 'hold': 'Hold Only'}
            ).classes('w-32')

            # Stats display
            stats_row = ui.row().classes('ml-auto gap-4 items-center')

    # ===== DECISION TIMELINE SECTION =====
    with ui.card().classes('w-full p-4 mb-6'):
        ui.label('Trade Decisions Timeline').classes('text-xl font-bold text-white mb-2')

        # Timeline container
        timeline_container = ui.column().classes('w-full')

    # Historical decisions storage
    historical_decisions = []

    # ===== AUTO-REFRESH LOGIC =====
    async def update_reasoning():
        """Update JSON editor and timeline with latest reasoning data"""
        state = state_manager.get_state()

        # Update JSON editor
        reasoning_data = state.last_reasoning
        if reasoning_data and (reasoning_data.get('reasoning') or reasoning_data.get('trade_decisions')):
            json_editor.content = {'json': reasoning_data}
            json_editor.update()

            # Update timeline with filtering
            timeline_container.clear()
            with timeline_container:
                trade_decisions = reasoning_data.get('trade_decisions', [])

                # Add new decisions to history (avoiding duplicates)
                for decision in trade_decisions:
                    decision_id = f"{decision.get('asset')}_{decision.get('action')}_{decision.get('entry_price')}"
                    if not any(d.get('_id') == decision_id for d in historical_decisions):
                        decision['_id'] = decision_id
                        decision['timestamp'] = datetime.now().isoformat()
                        historical_decisions.insert(0, decision)  # Add to front of list
                        # Keep only last 20 decisions
                        if len(historical_decisions) > 20:
                            historical_decisions.pop()

                if trade_decisions:
                    # Apply filter
                    selected_filter = action_filter.value.upper()
                    filtered_decisions = [
                        d for d in trade_decisions
                        if selected_filter == 'ALL' or d.get('action', 'HOLD').upper() == selected_filter
                    ]

                    # Update stats
                    stats_row.clear()
                    with stats_row:
                        buy_count = len([d for d in trade_decisions if d.get('action', '').upper() == 'BUY'])
                        sell_count = len([d for d in trade_decisions if d.get('action', '').upper() == 'SELL'])
                        hold_count = len([d for d in trade_decisions if d.get('action', '').upper() == 'HOLD'])

                        ui.label(f'🟢 Buys: {buy_count}').classes('text-xs text-green-400 font-bold')
                        ui.label(f'🔴 Sells: {sell_count}').classes('text-xs text-red-400 font-bold')
                        ui.label(f'⚫ Holds: {hold_count}').classes('text-xs text-gray-400 font-bold')

                    if filtered_decisions:
                        # Create timeline with enhanced entries
                        with ui.timeline(side='right').classes('w-full'):
                            for decision in filtered_decisions:
                                asset = decision.get('asset', 'Unknown')
                                action = decision.get('action', 'hold').upper()
                                rationale = decision.get('rationale', 'No rationale provided')
                                allocation = decision.get('allocation_usd', 0)
                                tp_price = decision.get('tp_price')
                                sl_price = decision.get('sl_price')
                                exit_plan = decision.get('exit_plan', 'No exit plan')
                                entry_price = decision.get('entry_price', 'N/A')
                                confidence = decision.get('confidence', 0)

                                # Determine color based on action
                                if action == 'BUY':
                                    color = 'green'
                                    icon = '📈'
                                elif action == 'SELL':
                                    color = 'red'
                                    icon = '📉'
                                else:  # HOLD
                                    color = 'grey'
                                    icon = '⏸️'

                                # Timeline entry with enhanced details
                                with ui.timeline_entry(
                                    f'{icon} {asset} - {action}',
                                    color=color,
                                    icon='science'
                                ):
                                    # Confidence indicator
                                    if confidence:
                                        confidence_pct = int(confidence * 100) if confidence <= 1 else int(confidence)
                                        with ui.row().classes('items-center gap-2 mb-2'):
                                            ui.linear_progress(value=confidence).classes('flex-grow')
                                            ui.label(f'{confidence_pct}%').classes('text-xs text-gray-400 w-12')

                                    # Rationale
                                    ui.label(rationale).classes('text-sm text-gray-300 mb-2')

                                    # Details in grid
                                    with ui.grid(columns=2).classes('gap-2 text-xs text-gray-400'):
                                        ui.label(f'Entry: {entry_price}')
                                        ui.label(f'Allocation: ${allocation:,.2f}')
                                        ui.label(f'TP: {tp_price if tp_price else "N/A"}')
                                        ui.label(f'SL: {sl_price if sl_price else "N/A"}')
                                        ui.label(f'Exit Plan: {exit_plan[:50]}...' if len(str(exit_plan)) > 50 else f'Exit Plan: {exit_plan}', column_span=2)
                    else:
                        ui.label(f'No {action_filter.value} decisions in current batch').classes('text-gray-400 text-center py-4')
                else:
                    ui.label('No trade decisions yet').classes('text-gray-400 text-center py-4')
        else:
            # Empty state
            json_editor.content = {'json': {}}
            json_editor.update()
            timeline_container.clear()

            # Update stats in empty state
            stats_row.clear()
            with stats_row:
                ui.label('🟢 Buys: 0').classes('text-xs text-green-400 font-bold')
                ui.label('🔴 Sells: 0').classes('text-xs text-red-400 font-bold')
                ui.label('⚫ Holds: 0').classes('text-xs text-gray-400 font-bold')

            with timeline_container:
                with ui.column().classes('items-center py-8'):
                    ui.label('🧠').classes('text-6xl mb-4')
                    ui.label('No reasoning data available').classes('text-xl text-gray-400 mb-2')
                    ui.label('Start the bot from the Dashboard to see AI decisions').classes('text-sm text-gray-500')

    # Action filter change handler
    def on_filter_change(value):
        """Handle filter change"""
        asyncio.create_task(update_reasoning())

    action_filter.on('update:model-value', on_filter_change)

    # Auto-refresh every 3 seconds
    ui.timer(3.0, update_reasoning)

    # Initial update
    asyncio.create_task(update_reasoning())
