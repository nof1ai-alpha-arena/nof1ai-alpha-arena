"""
Positions Page - Active trading positions with real-time PnL tracking
"""

from nicegui import ui
from src.gui.services.bot_service import BotService
from src.gui.services.state_manager import StateManager


def create_positions(bot_service: BotService, state_manager: StateManager):
    """Create positions page with live table and action buttons"""
    
    ui.label('Active Positions').classes('text-3xl font-bold mb-4 text-white')
    
    # Summary cards
    with ui.row().classes('w-full gap-4 mb-6'):
        # Total Positions
        with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-blue-600 to-blue-800'):
            positions_count = ui.label('0').classes('text-3xl font-bold text-white')
            ui.label('Total Positions').classes('text-sm text-gray-200 mt-1')
        
        # Total Unrealized PnL
        with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-purple-600 to-purple-800'):
            total_pnl = ui.label('$0.00').classes('text-3xl font-bold text-white')
            ui.label('Unrealized PnL').classes('text-sm text-gray-200 mt-1')
        
        # Total Exposure
        with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-indigo-600 to-indigo-800'):
            total_exposure = ui.label('$0.00').classes('text-3xl font-bold text-white')
            ui.label('Total Exposure').classes('text-sm text-gray-200 mt-1')
    
    # Positions table
    with ui.card().classes('w-full p-4'):
        ui.label('Position Details').classes('text-xl font-bold text-white mb-4')
        
        # Table columns definition
        columns = [
            {'name': 'symbol', 'label': 'Asset', 'field': 'symbol', 'align': 'left', 'sortable': True},
            {'name': 'side', 'label': 'Side', 'field': 'side', 'align': 'center', 'sortable': True},
            {'name': 'quantity', 'label': 'Size', 'field': 'quantity', 'align': 'right', 'sortable': True},
            {'name': 'entry_price', 'label': 'Entry Price', 'field': 'entry_price', 'align': 'right', 'sortable': True},
            {'name': 'current_price', 'label': 'Current Price', 'field': 'current_price', 'align': 'right', 'sortable': True},
            {'name': 'unrealized_pnl', 'label': 'Unrealized PnL', 'field': 'unrealized_pnl', 'align': 'right', 'sortable': True},
            {'name': 'pnl_pct', 'label': 'PnL %', 'field': 'pnl_pct', 'align': 'right', 'sortable': True},
            {'name': 'leverage', 'label': 'Leverage', 'field': 'leverage', 'align': 'center', 'sortable': True},
            {'name': 'liquidation_price', 'label': 'Liq. Price', 'field': 'liquidation_price', 'align': 'right', 'sortable': True},
            {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
        ]
        
        # Create table
        table = ui.table(
            columns=columns,
            rows=[],
            row_key='symbol',
            pagination={'rowsPerPage': 10, 'sortBy': 'unrealized_pnl', 'descending': True}
        ).classes('w-full')
        
        # Custom cell rendering for colored PnL
        table.add_slot('body-cell-unrealized_pnl', '''
            <q-td :props="props">
                <span :class="props.row.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'" class="font-bold">
                    {{ props.row.unrealized_pnl >= 0 ? '+' : '' }}${{ props.row.unrealized_pnl.toFixed(2) }}
                </span>
            </q-td>
        ''')
        
        # Custom cell rendering for PnL %
        table.add_slot('body-cell-pnl_pct', '''
            <q-td :props="props">
                <span :class="props.row.pnl_pct >= 0 ? 'text-green-500' : 'text-red-500'" class="font-bold">
                    {{ props.row.pnl_pct >= 0 ? '+' : '' }}{{ props.row.pnl_pct.toFixed(2) }}%
                </span>
            </q-td>
        ''')
        
        # Custom cell rendering for Side
        table.add_slot('body-cell-side', '''
            <q-td :props="props">
                <q-badge :color="props.row.side === 'LONG' ? 'green' : 'red'" :label="props.row.side" />
            </q-td>
        ''')
        
        # Custom cell rendering for Actions
        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat dense icon="show_chart" color="blue" size="sm" @click="$parent.$emit('chart', props.row)">
                    <q-tooltip>View Chart</q-tooltip>
                </q-btn>
                <q-btn flat dense icon="close" color="red" size="sm" @click="$parent.$emit('close', props.row)">
                    <q-tooltip>Close Position</q-tooltip>
                </q-btn>
            </q-td>
        ''')
        
        # Chart dialog
        chart_dialog = ui.dialog()
        with chart_dialog, ui.card().classes('w-96'):
            dialog_title = ui.label('').classes('text-xl font-bold mb-4')
            dialog_content = ui.label('Chart functionality coming soon...').classes('text-gray-400')
            ui.button('Close', on_click=chart_dialog.close).classes('mt-4')
        
        # Close confirmation dialog
        close_dialog = ui.dialog()
        with close_dialog, ui.card().classes('w-96'):
            close_title = ui.label('').classes('text-xl font-bold mb-4')
            close_message = ui.label('').classes('text-gray-300 mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=close_dialog.close).classes('bg-gray-600')
                close_confirm_btn = ui.button('Close Position', on_click=lambda: None).classes('bg-red-600')
        
        # Event handlers
        current_position = {'symbol': None}
        
        def show_chart(e):
            """Show chart dialog for position"""
            position = e.args
            dialog_title.text = f"{position['symbol']} Chart"
            chart_dialog.open()
        
        async def show_close_dialog(e):
            """Show close confirmation dialog"""
            position = e.args
            current_position['symbol'] = position['symbol']
            close_title.text = f"Close {position['symbol']} Position?"
            close_message.text = f"Are you sure you want to close your {position['side']} position in {position['symbol']}?\n\nCurrent PnL: ${position['unrealized_pnl']:.2f} ({position['pnl_pct']:+.2f}%)"
            close_dialog.open()
        
        async def confirm_close():
            """Confirm position closing"""
            symbol = current_position['symbol']
            if symbol:
                try:
                    close_dialog.close()
                    ui.notify(f'Closing {symbol} position...', type='info')
                    
                    success = await bot_service.close_position(symbol)
                    
                    if success:
                        ui.notify(f'Successfully closed {symbol} position!', type='positive')
                    else:
                        ui.notify(f'Failed to close {symbol} position', type='negative')
                except Exception as e:
                    ui.notify(f'Error closing position: {str(e)}', type='negative')
        
        # Wire up event handlers
        table.on('chart', show_chart)
        table.on('close', show_close_dialog)
        close_confirm_btn.on('click', confirm_close)
    
    # Empty state message
    empty_message = ui.label('No active positions').classes('text-center text-gray-500 text-lg mt-8')
    empty_message.visible = True
    
    # Update function
    async def update_positions():
        """Update positions table with latest data"""
        try:
            state = state_manager.get_state()
            positions = state.positions or []
            
            # Show/hide empty message
            empty_message.visible = len(positions) == 0
            table.visible = len(positions) > 0
            
            if positions:
                # Calculate summary metrics
                total_unrealized_pnl = sum(p.get('unrealized_pnl', 0) for p in positions)
                total_notional = sum(abs(p.get('quantity', 0) * p.get('current_price', 0)) for p in positions)
                
                # Update summary cards
                positions_count.text = str(len(positions))
                total_pnl.text = f"${total_unrealized_pnl:+,.2f}"
                if total_unrealized_pnl >= 0:
                    total_pnl.classes(remove='text-red-500', add='text-green-500')
                else:
                    total_pnl.classes(remove='text-green-500', add='text-red-500')
                
                total_exposure.text = f"${total_notional:,.2f}"
                
                # Format positions for table
                rows = []
                for pos in positions:
                    quantity = pos.get('quantity', 0)
                    entry_price = pos.get('entry_price', 0)
                    current_price = pos.get('current_price', 0)
                    unrealized_pnl = pos.get('unrealized_pnl', 0)
                    
                    # Calculate PnL percentage
                    pnl_pct = 0
                    if entry_price > 0:
                        if quantity > 0:  # LONG
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        else:  # SHORT
                            pnl_pct = ((entry_price - current_price) / entry_price) * 100
                    
                    rows.append({
                        'symbol': pos.get('symbol', ''),
                        'side': 'LONG' if quantity > 0 else 'SHORT',
                        'quantity': abs(quantity),
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'unrealized_pnl': unrealized_pnl,
                        'pnl_pct': pnl_pct,
                        'leverage': pos.get('leverage', 1),
                        'liquidation_price': pos.get('liquidation_price', 0),
                    })
                
                table.rows = rows
                table.update()
            else:
                # Clear summary when no positions
                positions_count.text = '0'
                total_pnl.text = '$0.00'
                total_exposure.text = '$0.00'
        
        except Exception as e:
            ui.notify(f'Error updating positions: {str(e)}', type='warning')
    
    # Auto-refresh every 2 seconds
    ui.timer(2.0, update_positions)
    
    # Initial update
    # Note: Can't await in sync context, timer will handle it
