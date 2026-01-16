"""
History Page - Trade history with filters and CSV export
"""

import csv
from datetime import datetime
from nicegui import ui
from src.gui.services.bot_service import BotService
from src.gui.services.state_manager import StateManager


def create_history(bot_service: BotService, state_manager: StateManager):
    """Create history page with filters, table, and CSV export"""

    with ui.column().classes('w-full items-start'):
        ui.label('Trade History').classes('text-3xl font-bold mb-4 text-white')

        # Filters section
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label('Filters').classes('text-xl font-bold text-white mb-4')

            with ui.row().classes('w-full gap-4 items-center'):
                # Asset filter
                asset_filter = ui.select(
                    label='Asset',
                    options=['All'] + bot_service.get_assets(),
                    value='All'
                ).classes('flex-1')

                # Action filter
                action_filter = ui.select(
                    label='Action',
                    options=['All', 'buy', 'sell', 'hold'],
                    value='All'
                ).classes('flex-1')

                # Limit filter
                limit_filter = ui.number(
                    label='Max Results',
                    value=100,
                    min=10,
                    max=1000,
                    step=10
                ).classes('flex-1')

                # Apply button
                apply_btn = ui.button('Apply Filters', on_click=lambda: None).classes('bg-blue-600 px-6')

                # Export CSV button
                export_btn = ui.button('📥 Export CSV', on_click=lambda: None).classes('bg-green-600 px-6')

        # Statistics cards
        with ui.row().classes('w-full gap-4 mb-6'):
            # Total Trades
            with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-cyan-600 to-cyan-800'):
                total_trades = ui.label('0').classes('text-3xl font-bold text-white')
                ui.label('Total Trades').classes('text-sm text-gray-200 mt-1')

            # Win Rate
            with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-green-600 to-green-800'):
                win_rate = ui.label('0%').classes('text-3xl font-bold text-white')
                ui.label('Win Rate').classes('text-sm text-gray-200 mt-1')

            # Total PnL
            with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-purple-600 to-purple-800'):
                total_pnl_label = ui.label('$0.00').classes('text-3xl font-bold text-white')
                ui.label('Total PnL').classes('text-sm text-gray-200 mt-1')

        # Trade history table
        with ui.card().classes('w-full p-4'):
            ui.label('Trade Log').classes('text-xl font-bold text-white mb-4')

            # Table columns
            columns = [
                {'name': 'timestamp', 'label': 'Time', 'field': 'timestamp', 'align': 'left', 'sortable': True},
                {'name': 'asset', 'label': 'Asset', 'field': 'asset', 'align': 'center', 'sortable': True},
                {'name': 'action', 'label': 'Action', 'field': 'action', 'align': 'center', 'sortable': True},
                {'name': 'entry_price', 'label': 'Entry', 'field': 'entry_price', 'align': 'right', 'sortable': True},
                {'name': 'exit_price', 'label': 'Exit', 'field': 'exit_price', 'align': 'right', 'sortable': True},
                {'name': 'size', 'label': 'Size', 'field': 'size', 'align': 'right', 'sortable': True},
                {'name': 'pnl', 'label': 'PnL', 'field': 'pnl', 'align': 'right', 'sortable': True},
                {'name': 'pnl_pct', 'label': 'PnL %', 'field': 'pnl_pct', 'align': 'right', 'sortable': True},
                {'name': 'rationale', 'label': 'Rationale', 'field': 'rationale', 'align': 'left'},
            ]

            # Create table
            table = ui.table(
                columns=columns,
                rows=[],
                row_key='timestamp',
                pagination={'rowsPerPage': 20, 'sortBy': 'timestamp', 'descending': True}
            ).classes('w-full')

            # Custom cell rendering for Action
            table.add_slot('body-cell-action', '''
                <q-td :props="props">
                    <q-badge
                        :color="props.row.action === 'buy' ? 'green' : props.row.action === 'sell' ? 'red' : 'grey'"
                        :label="props.row.action.toUpperCase()"
                    />
                </q-td>
            ''')

            # Custom cell rendering for PnL
            table.add_slot('body-cell-pnl', '''
                <q-td :props="props">
                    <span v-if="props.row.pnl !== null" :class="props.row.pnl >= 0 ? 'text-green-500' : 'text-red-500'" class="font-bold">
                        {{ props.row.pnl >= 0 ? '+' : '' }}${{ props.row.pnl.toFixed(2) }}
                    </span>
                    <span v-else class="text-gray-500">-</span>
                </q-td>
            ''')

            # Custom cell rendering for PnL %
            table.add_slot('body-cell-pnl_pct', '''
                <q-td :props="props">
                    <span v-if="props.row.pnl_pct !== null" :class="props.row.pnl_pct >= 0 ? 'text-green-500' : 'text-red-500'" class="font-bold">
                        {{ props.row.pnl_pct >= 0 ? '+' : '' }}{{ props.row.pnl_pct.toFixed(2) }}%
                    </span>
                    <span v-else class="text-gray-500">-</span>
                </q-td>
            ''')

            # Custom cell rendering for Rationale (truncated with tooltip)
            table.add_slot('body-cell-rationale', '''
                <q-td :props="props">
                    <div class="text-sm text-gray-400 truncate max-w-xs cursor-pointer" @click="$parent.$emit('detail', props.row)">
                        {{ props.row.rationale ? props.row.rationale.substring(0, 50) + '...' : 'No rationale' }}
                    </div>
                </q-td>
            ''')

            # Detail dialog
            detail_dialog = ui.dialog()
            with detail_dialog, ui.card().classes('w-[600px]'):
                detail_title = ui.label('').classes('text-xl font-bold mb-4')
                with ui.column().classes('gap-2'):
                    detail_asset = ui.label('').classes('text-gray-300')
                    detail_action = ui.label('').classes('text-gray-300')
                    detail_prices = ui.label('').classes('text-gray-300')
                    detail_pnl = ui.label('').classes('text-gray-300')
                    ui.separator()
                    detail_rationale = ui.label('').classes('text-gray-400 whitespace-pre-wrap')
                ui.button('Close', on_click=detail_dialog.close).classes('mt-4')

            def show_detail(e):
                """Show trade detail dialog"""
                trade = e.args
                detail_title.text = f"Trade Details - {trade['asset']}"
                detail_asset.text = f"Asset: {trade['asset']}"
                detail_action.text = f"Action: {trade['action'].upper()}"

                # Handle None values for prices
                entry_str = f"${trade['entry_price']:.2f}" if trade.get('entry_price') else 'N/A'
                exit_str = f"${trade['exit_price']:.2f}" if trade.get('exit_price') else 'N/A'
                detail_prices.text = f"Entry: {entry_str} | Exit: {exit_str}"

                if trade.get('pnl') is not None:
                    pnl_text = f"PnL: ${trade['pnl']:+.2f} ({trade['pnl_pct']:+.2f}%)"
                    detail_pnl.text = pnl_text
                else:
                    detail_pnl.text = "PnL: N/A"

                detail_rationale.text = f"Rationale:\n{trade.get('rationale') or 'No rationale provided'}"
                detail_dialog.open()

            table.on('detail', show_detail)

        # Empty state message
        empty_message = ui.label('No trade history available').classes('text-center text-gray-500 text-lg mt-8')
        empty_message.visible = True

    # Current filter state
    current_filters = {
        'asset': 'All',
        'action': 'All',
        'limit': 100
    }

    # Update function
    async def update_history():
        """Update trade history table"""
        try:
            # Get filtered trade history
            asset = None if current_filters['asset'] == 'All' else current_filters['asset']
            action = None if current_filters['action'] == 'All' else current_filters['action']
            limit = int(current_filters['limit'])

            trades = bot_service.get_trade_history(asset=asset, action=action, limit=limit)

            # Show/hide empty message
            empty_message.visible = len(trades) == 0
            table.visible = len(trades) > 0

            if trades:
                # Calculate statistics
                total_count = len(trades)
                profitable_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
                win_rate_pct = (profitable_trades / total_count * 100) if total_count > 0 else 0
                total_pnl_value = sum(t.get('pnl', 0) for t in trades if t.get('pnl') is not None)

                # Update statistics cards
                total_trades.text = str(total_count)
                win_rate.text = f"{win_rate_pct:.1f}%"
                total_pnl_label.text = f"${total_pnl_value:+,.2f}"
                if total_pnl_value >= 0:
                    total_pnl_label.classes(remove='text-red-500', add='text-green-500')
                else:
                    total_pnl_label.classes(remove='text-green-500', add='text-red-500')

                # Format trades for table
                rows = []
                for trade in trades:
                    # Parse timestamp
                    timestamp = trade.get('timestamp', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            timestamp_str = timestamp
                    else:
                        timestamp_str = 'N/A'

                    rows.append({
                        'timestamp': timestamp_str,
                        'asset': trade.get('asset', 'N/A'),
                        'action': trade.get('action', 'N/A'),
                        'entry_price': trade.get('entry_price', 0),
                        'exit_price': trade.get('exit_price'),
                        'size': trade.get('size', 0),
                        'pnl': trade.get('pnl'),
                        'pnl_pct': trade.get('pnl_pct'),
                        'rationale': trade.get('rationale', ''),
                    })

                table.rows = rows
                table.update()
            else:
                # Clear statistics when no trades
                total_trades.text = '0'
                win_rate.text = '0%'
                total_pnl_label.text = '$0.00'

        except Exception as e:
            ui.notify(f'Error updating history: {str(e)}', type='warning')

    # Apply filters handler
    async def apply_filters():
        """Apply selected filters"""
        current_filters['asset'] = asset_filter.value
        current_filters['action'] = action_filter.value
        current_filters['limit'] = limit_filter.value
        await update_history()
        ui.notify('Filters applied', type='info')

    # Export CSV handler
    async def export_csv():
        """Export trade history to CSV"""
        try:
            # Get current filtered data
            asset = None if current_filters['asset'] == 'All' else current_filters['asset']
            action = None if current_filters['action'] == 'All' else current_filters['action']
            limit = int(current_filters['limit'])

            trades = bot_service.get_trade_history(asset=asset, action=action, limit=limit)

            if not trades:
                ui.notify('No trades to export', type='warning')
                return

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'trade_history_{timestamp}.csv'

            # Write CSV
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['timestamp', 'asset', 'action', 'entry_price', 'exit_price', 'size', 'pnl', 'pnl_pct', 'rationale']
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                writer.writeheader()
                for trade in trades:
                    writer.writerow({
                        'timestamp': trade.get('timestamp', ''),
                        'asset': trade.get('asset', ''),
                        'action': trade.get('action', ''),
                        'entry_price': trade.get('entry_price', 0),
                        'exit_price': trade.get('exit_price', ''),
                        'size': trade.get('size', 0),
                        'pnl': trade.get('pnl', ''),
                        'pnl_pct': trade.get('pnl_pct', ''),
                        'rationale': trade.get('rationale', ''),
                    })

            ui.notify(f'Exported {len(trades)} trades to {filename}', type='positive')

        except Exception as e:
            ui.notify(f'Error exporting CSV: {str(e)}', type='negative')

    # Wire up button handlers
    apply_btn.on('click', apply_filters)
    export_btn.on('click', export_csv)

    # Auto-refresh every 5 seconds
    ui.timer(5.0, update_history)

    # Initial update
    # Note: Can't await in sync context, timer will handle it
