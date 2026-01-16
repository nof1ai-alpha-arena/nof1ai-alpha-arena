"""
Dashboard Page - Main dashboard with metrics and charts
"""

import plotly.graph_objects as go
from nicegui import ui
from src.gui.services.bot_service import BotService
from src.gui.services.state_manager import StateManager


def create_dashboard(bot_service: BotService, state_manager: StateManager):
    """Create dashboard page with real-time metrics, charts, and controls"""

    ui.label('Dashboard').classes('text-3xl font-bold mb-4 text-white')

    # ===== METRICS CARDS (4 cards in grid) =====
    with ui.grid(columns=4).classes('w-full gap-4 mb-6'):
        # Card 1: Total Balance
        with ui.card().classes('metric-card'):
            balance_value = ui.label('$0.00').classes('text-4xl font-bold text-white')
            ui.label('Total Balance').classes('text-sm text-gray-200 mt-2')

        # Card 2: Total Return
        with ui.card().classes('metric-card'):
            return_value = ui.label('+0.00%').classes('text-4xl font-bold text-white')
            ui.label('Total Return').classes('text-sm text-gray-200 mt-2')

        # Card 3: Sharpe Ratio
        with ui.card().classes('metric-card'):
            sharpe_value = ui.label('0.00').classes('text-4xl font-bold text-white')
            ui.label('Sharpe Ratio').classes('text-sm text-gray-200 mt-2')

        # Card 4: Active Positions
        with ui.card().classes('metric-card'):
            positions_value = ui.label('0').classes('text-4xl font-bold text-white')
            ui.label('Active Positions').classes('text-sm text-gray-200 mt-2')

    # ===== CHARTS ROW =====
    with ui.row().classes('w-full gap-4 mb-6'):
        # Equity Curve Chart (left half)
        with ui.card().classes('flex-1 p-4'):
            ui.label('Portfolio Value').classes('text-xl font-bold text-white mb-2')

            equity_chart = ui.plotly(go.Figure(
                data=[go.Scatter(
                    x=[],
                    y=[],
                    mode='lines',
                    name='Value',
                    line=dict(color='#667eea', width=3)
                )],
                layout=go.Layout(
                    template='plotly_dark',
                    height=300,
                    margin=dict(l=50, r=20, t=20, b=40),
                    xaxis=dict(title='Time', showgrid=True, gridcolor='#374151'),
                    yaxis=dict(title='Value ($)', showgrid=True, gridcolor='#374151'),
                    paper_bgcolor='#1f2937',
                    plot_bgcolor='#1f2937',
                    font=dict(color='#e5e7eb')
                )
            )).classes('w-full')

        # Asset Allocation Pie Chart (right half)
        with ui.card().classes('flex-1 p-4'):
            ui.label('Asset Allocation').classes('text-xl font-bold text-white mb-2')

            allocation_chart = ui.plotly(go.Figure(
                data=[go.Pie(
                    labels=[],
                    values=[],
                    hole=0.4,
                    marker=dict(colors=['#667eea', '#764ba2', '#f093fb', '#4facfe'])
                )],
                layout=go.Layout(
                    template='plotly_dark',
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='#1f2937',
                    plot_bgcolor='#1f2937',
                    font=dict(color='#e5e7eb'),
                    showlegend=True,
                    legend=dict(orientation='v', x=1, y=0.5)
                )
            )).classes('w-full')

    # ===== MARKET DATA =====
    with ui.card().classes('w-full p-4 mb-6'):
        ui.label('Market Data').classes('text-xl font-bold text-white mb-2')
        market_data_container = ui.column().classes('w-full gap-4')
        
        with market_data_container:
            ui.label('No market data available').classes('text-gray-400 text-center py-4')

    # ===== ACTIVITY FEED =====
    with ui.card().classes('w-full p-4 mb-6'):
        ui.label('Recent Activity').classes('text-xl font-bold text-white mb-2')

        activity_log = ui.log(max_lines=10).classes('w-full h-48 bg-gray-900 text-gray-300 p-4 rounded')
        activity_log.push('Bot initialized. Waiting to start...')

    # ===== CONTROL PANEL =====
    with ui.card().classes('w-full p-4'):
        ui.label('Bot Controls').classes('text-xl font-bold text-white mb-4')

        with ui.row().classes('gap-4 items-center'):
            # Refresh Data Button (for manual mode)
            refresh_data_btn = ui.button('🔄 Refresh Data', on_click=lambda: refresh_market_data())
            refresh_data_btn.classes('bg-blue-600 hover:bg-blue-700 text-white px-6 py-3')
            refresh_data_loading = ui.label('').classes('text-sm text-blue-400 ml-2')

            # Start Button
            start_btn = ui.button('▶ Start Bot', on_click=lambda: start_bot())
            start_btn.classes('bg-green-600 hover:bg-green-700 text-white px-6 py-3')

            # Stop Button
            stop_btn = ui.button('⏹ Stop Bot', on_click=lambda: stop_bot())
            stop_btn.classes('bg-red-600 hover:bg-red-700 text-white px-6 py-3')
            stop_btn.props('disable')  # Initially disabled

            # Status indicator
            status_indicator = ui.label('⚫ Stopped').classes('text-lg font-bold ml-4')

        # Last refresh timestamp
        with ui.row().classes('gap-4 items-center mt-4'):
            last_refresh_label = ui.label('Last refreshed: Never').classes('text-sm text-gray-400')
            refresh_timer_label = ui.label('').classes('text-xs text-gray-500')

    # ===== CONTROL FUNCTIONS =====

    async def start_bot():
        """Start the trading bot"""
        try:
            status_indicator.text = '🟡 Starting...'
            activity_log.push('Starting bot...')

            await bot_service.start()

            status_indicator.text = '🟢 Running'
            status_indicator.classes(remove='text-gray-400', add='text-green-500')
            start_btn.props('disable')
            stop_btn.props(remove='disable')

            activity_log.push('✅ Bot started successfully!')
            ui.notify('Bot started!', type='positive')

        except Exception as e:
            status_indicator.text = '🔴 Error'
            status_indicator.classes(add='text-red-500')
            activity_log.push(f'❌ Error starting bot: {str(e)}')
            ui.notify(f'Failed to start: {str(e)}', type='negative')

    async def stop_bot():
        """Stop the trading bot"""
        try:
            status_indicator.text = '🟡 Stopping...'
            activity_log.push('Stopping bot...')

            await bot_service.stop()

            status_indicator.text = '⚫ Stopped'
            status_indicator.classes(remove='text-green-500', add='text-gray-400')
            start_btn.props(remove='disable')
            stop_btn.props('disable')

            activity_log.push('✅ Bot stopped successfully!')
            ui.notify('Bot stopped!', type='info')

        except Exception as e:
            activity_log.push(f'❌ Error stopping bot: {str(e)}')
            ui.notify(f'Failed to stop: {str(e)}', type='negative')

    # ===== AUTO-REFRESH FUNCTIONS =====

    import time
    import asyncio
    last_refresh_time = None
    refresh_seconds_ago = 0

    async def refresh_market_data():
        """Refresh market data from Hyperliquid without starting bot"""
        nonlocal last_refresh_time, refresh_seconds_ago

        try:
            refresh_data_btn.enabled = False
            refresh_data_loading.text = '⏳ Fetching...'
            activity_log.push('📊 Refreshing market data...')

            # Call bot service to refresh data
            success = await bot_service.refresh_market_data()

            if success:
                last_refresh_time = time.time()
                refresh_data_loading.text = '✅ Done'
                activity_log.push('✅ Market data refreshed successfully!')
                ui.notify('Market data refreshed!', type='positive')

                # Update dashboard immediately after refresh
                await update_dashboard()
            else:
                refresh_data_loading.text = '❌ Failed'
                activity_log.push('❌ Failed to refresh market data')
                ui.notify('Failed to refresh market data', type='negative')

        except Exception as e:
            activity_log.push(f'❌ Refresh error: {str(e)}')
            ui.notify(f'Error: {str(e)}', type='negative')
            refresh_data_loading.text = '❌ Error'
        finally:
            refresh_data_btn.enabled = True
            # Clear loading message after 2 seconds
            await asyncio.sleep(2.0)
            refresh_data_loading.text = ''

    async def update_dashboard():
        """Update all dashboard components with latest data"""
        nonlocal refresh_seconds_ago

        try:
            state = state_manager.get_state()

            # Update metrics cards
            balance_value.text = f'${state.balance:,.2f}'

            # Return with color coding
            return_pct = state.total_return_pct
            return_value.text = f'{return_pct:+.2f}%'
            if return_pct >= 0:
                return_value.classes(remove='text-red-500', add='text-green-500')
            else:
                return_value.classes(remove='text-green-500', add='text-red-500')

            sharpe_value.text = f'{state.sharpe_ratio:.2f}'
            positions_value.text = str(len(state.positions or []))

            # Update equity curve chart
            equity_history = bot_service.get_equity_history()
            if equity_history:
                times = [d['time'] for d in equity_history]
                values = [d['value'] for d in equity_history]

                equity_chart.figure.data[0].x = times
                equity_chart.figure.data[0].y = values
                equity_chart.update()

            # Update asset allocation chart
            positions = state.positions or []
            if positions:
                labels = [p['symbol'] for p in positions]
                values = [abs(p['quantity'] * p['entry_price']) for p in positions]

                allocation_chart.figure.data[0].labels = labels
                allocation_chart.figure.data[0].values = values
                allocation_chart.update()

            # Update market data
            market_data = getattr(state, 'market_data', None)
            market_data_container.clear()
            
            if market_data and isinstance(market_data, list) and len(market_data) > 0:
                with market_data_container:
                    with ui.grid(columns=len(market_data)).classes('w-full gap-4'):
                        for asset_data in market_data:
                            asset = asset_data.get('asset', 'N/A')
                            price = asset_data.get('current_price', 0)
                            
                            # Intraday data
                            intraday = asset_data.get('intraday', {})
                            ema20 = intraday.get('ema20', 0)
                            rsi14 = intraday.get('rsi14', 0)
                            
                            # Long-term data
                            lt = asset_data.get('long_term', {})
                            lt_ema20 = lt.get('ema20', 0)
                            lt_ema50 = lt.get('ema50', 0)
                            
                            with ui.card().classes('p-4 bg-gradient-to-br from-gray-700 to-gray-800'):
                                ui.label(asset).classes('text-2xl font-bold text-white mb-2')
                                ui.label(f'${price:,.2f}').classes('text-xl text-green-400 mb-3')
                                
                                with ui.column().classes('gap-1 text-sm'):
                                    ui.label(f'EMA20 (5m): {ema20:.2f}' if ema20 else 'EMA20: N/A').classes('text-gray-300')
                                    ui.label(f'RSI14 (5m): {rsi14:.2f}' if rsi14 else 'RSI14: N/A').classes('text-gray-300')
                                    ui.separator()
                                    ui.label(f'EMA20 (4h): {lt_ema20:.2f}' if lt_ema20 else 'EMA20 (4h): N/A').classes('text-gray-400')
                                    ui.label(f'EMA50 (4h): {lt_ema50:.2f}' if lt_ema50 else 'EMA50 (4h): N/A').classes('text-gray-400')
            else:
                with market_data_container:
                    ui.label('No market data available').classes('text-gray-400 text-center py-4')

            # Update activity log with recent events
            recent_events = bot_service.get_recent_events(limit=5)
            for event in recent_events[-5:]:  # Last 5 only
                activity_log.push(f"[{event['time']}] {event['message']}")

            # Update button states based on bot status
            if state.is_running:
                status_indicator.text = '🟢 Running'
                status_indicator.classes(remove='text-gray-400', add='text-green-500')
                start_btn.props('disable')
                stop_btn.props(remove='disable')
            else:
                status_indicator.text = '⚫ Stopped'
                status_indicator.classes(remove='text-green-500', add='text-gray-400')
                start_btn.props(remove='disable')
                stop_btn.props('disable')

            if state.error:
                status_indicator.text = '🔴 Error'
                status_indicator.classes(add='text-red-500')
                activity_log.push(f'Error: {state.error}')

            # Update refresh timestamp
            if last_refresh_time:
                refresh_seconds_ago = int(time.time() - last_refresh_time)
                if refresh_seconds_ago < 60:
                    last_refresh_label.text = f'Last refreshed: {refresh_seconds_ago} seconds ago'
                else:
                    minutes = refresh_seconds_ago // 60
                    last_refresh_label.text = f'Last refreshed: {minutes} minutes ago'
                refresh_timer_label.text = '(auto-updating)'
            else:
                last_refresh_label.text = 'Last refreshed: Never'
                refresh_timer_label.text = '(click Refresh Data to fetch data)'

        except Exception as e:
            activity_log.push(f'Dashboard update error: {str(e)}')

    # ===== AUTO-REFRESH TIMER =====
    # Update dashboard every 3 seconds
    ui.timer(3.0, update_dashboard)

    # Initial update (call immediately, but don't await in sync context)
    # The timer will handle subsequent updates
