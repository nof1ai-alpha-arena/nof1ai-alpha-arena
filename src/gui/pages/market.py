"""
Market Data Page - Live market data and technical indicators
"""

import plotly.graph_objects as go
from nicegui import ui
from src.gui.services.bot_service import BotService
from src.gui.services.state_manager import StateManager


def create_market(bot_service: BotService, state_manager: StateManager):
    """Create market data page with live prices and technical indicators"""

    ui.label('Market Data').classes('text-3xl font-bold mb-4 text-white')

    # ===== ASSET SELECTOR =====
    with ui.row().classes('w-full items-center gap-4 mb-6'):
        ui.label('Select Asset:').classes('text-lg font-semibold text-white')

        # Get assets from bot config
        state = state_manager.get_state()
        configured_assets = bot_service.get_assets() if bot_service.is_running() else ['BTC', 'ETH', 'SOL']
        available_assets = configured_assets if configured_assets else ['BTC', 'ETH', 'SOL']

        asset_select = ui.select(
            label='Asset',
            options=available_assets,
            value=available_assets[0] if available_assets else 'BTC'
        ).classes('w-48')

        interval_select = ui.select(
            label='Interval',
            options=['1m', '5m', '15m', '1h', '4h', '1d'],
            value='5m'
        ).classes('w-32')

    # ===== PRICE CARDS =====
    with ui.grid(columns=4).classes('w-full gap-4 mb-6'):
        # Current Price Card
        with ui.card().classes('metric-card'):
            current_price_label = ui.label('$0.00').classes('text-4xl font-bold text-white')
            ui.label('Current Price').classes('text-sm text-gray-200 mt-2')

        # 24h Change Card
        with ui.card().classes('metric-card'):
            change_24h_label = ui.label('+0.00%').classes('text-4xl font-bold text-green-400')
            ui.label('24h Change').classes('text-sm text-gray-200 mt-2')

        # 24h Volume Card
        with ui.card().classes('metric-card'):
            volume_24h_label = ui.label('$0.00M').classes('text-4xl font-bold text-white')
            ui.label('24h Volume').classes('text-sm text-gray-200 mt-2')

        # Open Interest Card
        with ui.card().classes('metric-card'):
            open_interest_label = ui.label('$0.00M').classes('text-4xl font-bold text-white')
            ui.label('Open Interest').classes('text-sm text-gray-200 mt-2')

    # ===== PRICE CHART =====
    with ui.card().classes('w-full p-4 mb-6'):
        ui.label('Price Chart').classes('text-xl font-bold text-white mb-2')

        # Candlestick chart
        price_chart = ui.plotly(go.Figure(
            data=[go.Candlestick(
                x=[],
                open=[],
                high=[],
                low=[],
                close=[],
                name='Price'
            )],
            layout=go.Layout(
                template='plotly_dark',
                height=400,
                margin=dict(l=50, r=20, t=20, b=40),
                xaxis=dict(title='Time', showgrid=True, gridcolor='#374151'),
                yaxis=dict(title='Price ($)', showgrid=True, gridcolor='#374151'),
                paper_bgcolor='#1f2937',
                plot_bgcolor='#1f2937',
                font=dict(color='#e5e7eb'),
                showlegend=True
            )
        )).classes('w-full')

    # ===== TECHNICAL INDICATORS =====
    with ui.row().classes('w-full gap-4 mb-6'):
        # Left column - Trend Indicators
        with ui.card().classes('flex-1 p-4'):
            ui.label('Trend Indicators').classes('text-xl font-bold text-white mb-4')

            with ui.column().classes('gap-3 w-full'):
                # EMA 20/50
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('EMA 20').classes('text-gray-300')
                    ema20_label = ui.label('$0.00').classes('text-white font-semibold')

                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('EMA 50').classes('text-gray-300')
                    ema50_label = ui.label('$0.00').classes('text-white font-semibold')

                ui.separator()

                # MACD
                ui.label('MACD').classes('text-lg font-bold text-white mt-2')
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('MACD Line').classes('text-gray-300')
                    macd_line_label = ui.label('0.00').classes('text-white font-semibold')

                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Signal Line').classes('text-gray-300')
                    macd_signal_label = ui.label('0.00').classes('text-white font-semibold')

                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Histogram').classes('text-gray-300')
                    macd_hist_label = ui.label('0.00').classes('text-green-400 font-semibold')

        # Right column - Momentum Indicators
        with ui.card().classes('flex-1 p-4'):
            ui.label('Momentum Indicators').classes('text-xl font-bold text-white mb-4')

            with ui.column().classes('gap-3 w-full'):
                # RSI
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('RSI (14)').classes('text-gray-300')
                    rsi_label = ui.label('50.00').classes('text-white font-semibold')

                # RSI Bar
                rsi_progress = ui.linear_progress(value=0.5, show_value=False).classes('w-full')

                ui.separator()

                # ATR
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('ATR (14)').classes('text-gray-300')
                    atr_label = ui.label('$0.00').classes('text-white font-semibold')

                ui.separator()

                # Stochastic
                ui.label('Stochastic').classes('text-lg font-bold text-white mt-2')
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('%K').classes('text-gray-300')
                    stoch_k_label = ui.label('50.00').classes('text-white font-semibold')

                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('%D').classes('text-gray-300')
                    stoch_d_label = ui.label('50.00').classes('text-white font-semibold')

    # ===== INDICATOR CHART =====
    with ui.card().classes('w-full p-4 mb-6'):
        ui.label('RSI & MACD').classes('text-xl font-bold text-white mb-2')

        # Create subplot for RSI and MACD
        indicator_chart = ui.plotly(go.Figure(
            data=[
                go.Scatter(x=[], y=[], mode='lines', name='RSI', line=dict(color='#f59e0b', width=2)),
                go.Scatter(x=[], y=[], mode='lines', name='MACD', line=dict(color='#3b82f6', width=2), yaxis='y2'),
            ],
            layout=go.Layout(
                template='plotly_dark',
                height=300,
                margin=dict(l=50, r=50, t=20, b=40),
                xaxis=dict(title='Time', showgrid=True, gridcolor='#374151'),
                yaxis=dict(title='RSI', showgrid=True, gridcolor='#374151', range=[0, 100]),
                yaxis2=dict(title='MACD', overlaying='y', side='right', showgrid=False),
                paper_bgcolor='#1f2937',
                plot_bgcolor='#1f2937',
                font=dict(color='#e5e7eb'),
                showlegend=True
            )
        )).classes('w-full')

    # ===== MARKET SENTIMENT =====
    with ui.card().classes('w-full p-4'):
        ui.label('Market Sentiment').classes('text-xl font-bold text-white mb-4')

        with ui.row().classes('w-full gap-6 items-center'):
            # Sentiment gauge
            with ui.column().classes('flex-1'):
                sentiment_label = ui.label('NEUTRAL').classes('text-3xl font-bold text-gray-400')
                sentiment_desc = ui.label('Waiting for clear signals').classes('text-sm text-gray-400 mt-2')

            # Signal indicators
            with ui.column().classes('flex-1'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    trend_icon = ui.label('○').classes('text-2xl text-gray-400')
                    ui.label('Trend Signal').classes('text-gray-300')

                with ui.row().classes('items-center gap-2 mb-2'):
                    momentum_icon = ui.label('○').classes('text-2xl text-gray-400')
                    ui.label('Momentum Signal').classes('text-gray-300')

                with ui.row().classes('items-center gap-2'):
                    volume_icon = ui.label('○').classes('text-2xl text-gray-400')
                    ui.label('Volume Signal').classes('text-gray-300')

    # ===== AUTO-REFRESH LOGIC =====
    async def update_market_data():
        """Update market data and indicators from real bot data"""
        state = state_manager.get_state()
        selected_asset = asset_select.value

        # Get market data for selected asset from bot state
        market_data = None
        if state.market_data:
            # market_data can be either dict with asset keys or list of dicts
            if isinstance(state.market_data, dict):
                market_data = state.market_data.get(selected_asset)
            elif isinstance(state.market_data, list):
                market_data = next((m for m in state.market_data if m.get('asset') == selected_asset), None)

        if not market_data:
            # No data available yet
            current_price_label.set_text('Loading...')
            change_24h_label.set_text('--')
            volume_24h_label.set_text('--')
            open_interest_label.set_text('--')
            return

        # Update price cards with real data
        current_price = market_data.get('price') or market_data.get('current_price', 0)
        current_price_label.set_text(f'${current_price:,.2f}')
        
        # 24h change (mock for now - need to calculate from price history)
        change_24h_label.set_text('+0.00%')
        change_24h_label.classes('text-4xl font-bold text-gray-400')
        
        # Volume and OI
        open_interest = market_data.get('open_interest', 0)
        if open_interest:
            open_interest_label.set_text(f'${open_interest/1e6:.1f}M')
        else:
            open_interest_label.set_text('--')
        
        volume_24h_label.set_text('--')  # Not available in current data
        
        # Update indicators - use 5m data from market_data
        intraday = market_data.get('intraday', {})
        long_term = market_data.get('long_term', {})
        
        # EMA values
        ema20_5m = intraday.get('ema20')
        ema20_lt = long_term.get('ema20')
        
        if ema20_5m:
            ema20_label.set_text(f'${ema20_5m:,.2f}')
        else:
            ema20_label.set_text('--')
        
        ema50_val = long_term.get('ema50')
        if ema50_val:
            ema50_label.set_text(f'${ema50_val:,.2f}')
        else:
            ema50_label.set_text('--')
        
        # MACD
        macd_val = intraday.get('macd')
        if macd_val:
            macd_line_label.set_text(f'{macd_val:.2f}')
        else:
            macd_line_label.set_text('--')
        
        macd_signal_label.set_text('--')  # Not separate in current data
        macd_hist_label.set_text('--')
        
        # RSI
        rsi_value = intraday.get('rsi14')
        if rsi_value:
            rsi_label.set_text(f'{rsi_value:.2f}')
            rsi_progress.set_value(rsi_value / 100)
            
            if rsi_value > 70:
                rsi_label.classes('text-red-400 font-semibold')
            elif rsi_value < 30:
                rsi_label.classes('text-green-400 font-semibold')
            else:
                rsi_label.classes('text-white font-semibold')
        else:
            rsi_label.set_text('--')
            rsi_progress.set_value(0.5)
        
        # ATR
        atr_val = long_term.get('atr14')
        if atr_val:
            atr_label.set_text(f'${atr_val:.2f}')
        else:
            atr_label.set_text('--')
        
        stoch_k_label.set_text('--')  # Not available
        stoch_d_label.set_text('--')
        
        # Update sentiment based on indicators
        if rsi_value and ema20_5m and current_price:
            if rsi_value > 60 and current_price > ema20_5m:
                sentiment_label.set_text('BULLISH')
                sentiment_label.classes('text-3xl font-bold text-green-400')
                sentiment_desc.set_text('Price above EMA20, RSI showing strength')
                trend_icon.set_text('●')
                trend_icon.classes('text-2xl text-green-400')
            elif rsi_value < 40 and current_price < ema20_5m:
                sentiment_label.set_text('BEARISH')
                sentiment_label.classes('text-3xl font-bold text-red-400')
                sentiment_desc.set_text('Price below EMA20, RSI showing weakness')
                trend_icon.set_text('●')
                trend_icon.classes('text-2xl text-red-400')
            else:
                sentiment_label.set_text('NEUTRAL')
                sentiment_label.classes('text-3xl font-bold text-gray-400')
                sentiment_desc.set_text('Mixed signals, waiting for clear direction')
                trend_icon.set_text('○')
                trend_icon.classes('text-2xl text-gray-400')
        else:
            sentiment_label.set_text('NO DATA')
            sentiment_label.classes('text-3xl font-bold text-gray-500')
            sentiment_desc.set_text('Waiting for market data from bot...')
        
        momentum_icon.set_text('○')
        momentum_icon.classes('text-2xl text-gray-400')
        volume_icon.set_text('○')
        volume_icon.classes('text-2xl text-gray-400')

    # Auto-refresh every 5 seconds
    ui.timer(5.0, update_market_data)

    # Refresh on asset/interval change
    asset_select.on('update:model-value', lambda: update_market_data())
    interval_select.on('update:model-value', lambda: update_market_data())
