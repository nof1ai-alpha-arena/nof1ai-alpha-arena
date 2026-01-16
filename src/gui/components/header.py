"""
Header Component - Top navigation bar with quick metrics
"""

from nicegui import ui
from src.gui.services.state_manager import StateManager


def create_header(state_manager: StateManager):
    """
    Create header component with logo, quick metrics, and status.

    Args:
        state_manager: Global state manager instance
    """
    with ui.row().classes('w-full bg-gray-900 px-6 py-3 shadow-lg items-center'):
        with ui.row().classes('w-full items-center justify-between'):
            # Logo and title
            with ui.row().classes('items-center gap-2'):
                ui.label('🤖').classes('text-3xl')
                ui.label('AI Trading Bot').classes('text-2xl font-bold text-white')

            # Quick metrics
            with ui.row().classes('gap-8'):
                # Balance
                with ui.column().classes('text-center'):
                    balance_label = ui.label('$0.00').classes('text-xl font-bold text-white')
                    ui.label('Balance').classes('text-xs text-gray-400')

                # 24h PnL
                with ui.column().classes('text-center'):
                    pnl_label = ui.label('+0.00%').classes('text-xl font-bold text-green-500')
                    ui.label('Total Return').classes('text-xs text-gray-400')

                # Sharpe Ratio
                with ui.column().classes('text-center'):
                    sharpe_label = ui.label('0.00').classes('text-xl font-bold text-white')
                    ui.label('Sharpe').classes('text-xs text-gray-400')

                # Status indicator
                with ui.column().classes('text-center'):
                    status_label = ui.label('⚫ Stopped').classes('text-sm font-bold')

            # Auto-refresh metrics
            async def update_header():
                state = state_manager.get_state()

                # Update balance
                balance_label.text = f"${state.balance:,.2f}"

                # Update PnL with color coding
                pnl_pct = state.total_return_pct
                pnl_label.text = f"{pnl_pct:+.2f}%"
                if pnl_pct >= 0:
                    pnl_label.classes(remove='text-red-500', add='text-green-500')
                else:
                    pnl_label.classes(remove='text-green-500', add='text-red-500')

                # Update Sharpe
                sharpe_label.text = f"{state.sharpe_ratio:.2f}"

                # Update status
                if state.is_running:
                    status_label.text = '🟢 Running'
                    status_label.classes(remove='text-gray-400', add='text-green-500')
                else:
                    status_label.text = '⚫ Stopped'
                    status_label.classes(remove='text-green-500', add='text-gray-400')

                # Error indicator
                if state.error:
                    status_label.text = '🔴 Error'
                    status_label.classes(remove='text-green-500 text-gray-400', add='text-red-500')

            # Refresh every second
            ui.timer(1.0, update_header)
