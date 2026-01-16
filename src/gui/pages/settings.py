"""
Settings Page - Configuration management with tabs
"""

import asyncio
import json
import os
from pathlib import Path
from nicegui import ui
from src.gui.services.bot_service import BotService
from src.gui.services.state_manager import StateManager
from src.backend.config_loader import CONFIG


def create_settings(bot_service: BotService, state_manager: StateManager):
    """Create settings page with 4 tabs for configuration"""

    ui.label('Settings').classes('text-3xl font-bold mb-4 text-white')

    # Configuration file path
    config_file = Path('data/config.json')

    # Load configuration from file or use defaults
    def load_config():
        """Load configuration from file"""
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                ui.notify(f'Failed to load config: {e}', type='warning')

        # Return defaults from environment
        return {
            'strategy': {
                'assets': CONFIG.get('assets') or 'BTC ETH',
                'interval': CONFIG.get('interval') or '5m',
                'llm_model': CONFIG.get('llm_model') or 'x-ai/grok-4',
                'reasoning_enabled': CONFIG.get('reasoning_enabled', False),
                'reasoning_effort': CONFIG.get('reasoning_effort') or 'high'
            },
            'api_keys': {
                'taapi_api_key': CONFIG.get('taapi_api_key') or '',
                'hyperliquid_private_key': CONFIG.get('hyperliquid_private_key') or '',
                'hyperliquid_network': CONFIG.get('hyperliquid_network') or 'mainnet',
                'openrouter_api_key': CONFIG.get('openrouter_api_key') or ''
            },
            'risk_management': {
                'max_position_size': 1000,
                'max_leverage': 3,
                'stop_loss_pct': 5,
                'take_profit_pct': 10,
                'max_open_positions': 5
            },
            'notifications': {
                'desktop_enabled': True,
                'telegram_enabled': False,
                'telegram_token': '',
                'telegram_chat_id': ''
            }
        }

    def save_config(config_data):
        """Save configuration to file"""
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            return True
        except Exception as e:
            ui.notify(f'Failed to save config: {e}', type='negative')
            return False

    # Load initial configuration
    config_data = load_config()

    # ===== TABBED INTERFACE =====
    with ui.card().classes('w-full p-4'):
        with ui.tabs().classes('w-full') as tabs:
            tab_strategy = ui.tab('Strategy', icon='analytics')
            tab_api = ui.tab('API Keys', icon='key')
            tab_risk = ui.tab('Risk Management', icon='shield')
            tab_notifications = ui.tab('Notifications', icon='notifications')

        with ui.tab_panels(tabs, value=tab_strategy).classes('w-full'):
            # ===== TAB 1: STRATEGY CONFIGURATION =====
            with ui.tab_panel(tab_strategy):
                ui.label('Strategy Configuration').classes('text-2xl font-bold mb-4 text-white')

                with ui.column().classes('gap-4 w-full max-w-2xl'):
                    # Assets input
                    ui.label('Trading Assets').classes('text-lg font-semibold text-white')
                    assets_input = ui.textarea(
                        label='Assets (comma-separated)',
                        placeholder='BTC, ETH, SOL',
                        value=config_data['strategy']['assets']
                    ).classes('w-full')
                    ui.label('Example: BTC, ETH, SOL or BTC ETH SOL').classes('text-xs text-gray-400')

                    ui.separator()

                    # Interval selection
                    ui.label('Trading Interval').classes('text-lg font-semibold text-white')
                    interval_select = ui.select(
                        label='Interval',
                        options=['1m', '5m', '15m', '1h', '4h'],
                        value=config_data['strategy']['interval']
                    ).classes('w-full')
                    ui.label('Timeframe for trading decisions').classes('text-xs text-gray-400')

                    ui.separator()

                    # LLM Model selection
                    ui.label('LLM Model').classes('text-lg font-semibold text-white')
                    llm_model_select = ui.select(
                        label='Model',
                        options=[
                            'x-ai/grok-4',
                            'openai/gpt-4',
                            'anthropic/claude-3.5-sonnet',
                            'deepseek/deepseek-chat-v3.1'
                        ],
                        value=config_data['strategy']['llm_model']
                    ).classes('w-full')
                    ui.label('LLM model for trading decisions').classes('text-xs text-gray-400')

                    ui.separator()

                    # Reasoning configuration
                    with ui.row().classes('items-center gap-4'):
                        reasoning_enabled = ui.checkbox(
                            'Enable Reasoning Tokens',
                            value=config_data['strategy']['reasoning_enabled']
                        )
                        ui.label('Use extended reasoning for better decisions').classes('text-sm text-gray-400')

                    reasoning_effort = ui.select(
                        label='Reasoning Effort',
                        options=['low', 'medium', 'high'],
                        value=config_data['strategy']['reasoning_effort']
                    ).classes('w-full')

                    ui.separator()

                    # Save and Load buttons
                    async def save_strategy_config():
                        try:
                            # Update config data
                            config_data['strategy']['assets'] = assets_input.value
                            config_data['strategy']['interval'] = interval_select.value
                            config_data['strategy']['llm_model'] = llm_model_select.value
                            config_data['strategy']['reasoning_enabled'] = reasoning_enabled.value
                            config_data['strategy']['reasoning_effort'] = reasoning_effort.value

                            # Save to file
                            if save_config(config_data):
                                # Update bot service config
                                assets_list = [a.strip() for a in config_data['strategy']['assets'].replace(',', ' ').split() if a.strip()]
                                bot_service.update_config({
                                    'assets': assets_list,
                                    'interval': config_data['strategy']['interval'],
                                    'model': config_data['strategy']['llm_model']
                                })
                                ui.notify('Strategy configuration saved successfully!', type='positive')
                            else:
                                ui.notify('Failed to save configuration', type='negative')
                        except Exception as e:
                            ui.notify(f'Error saving config: {str(e)}', type='negative')

                    async def load_strategy_config():
                        try:
                            loaded_config = load_config()
                            assets_input.value = loaded_config['strategy']['assets']
                            interval_select.value = loaded_config['strategy']['interval']
                            llm_model_select.value = loaded_config['strategy']['llm_model']
                            reasoning_enabled.value = loaded_config['strategy']['reasoning_enabled']
                            reasoning_effort.value = loaded_config['strategy']['reasoning_effort']
                            ui.notify('Configuration loaded successfully!', type='positive')
                        except Exception as e:
                            ui.notify(f'Error loading config: {str(e)}', type='negative')

                    with ui.row().classes('gap-2'):
                        ui.button('Save Configuration', on_click=save_strategy_config, icon='save').props('color=primary')
                        ui.button('Load Configuration', on_click=load_strategy_config, icon='refresh').props('color=secondary')

            # ===== TAB 2: API KEYS =====
            with ui.tab_panel(tab_api):
                ui.label('API Keys Configuration').classes('text-2xl font-bold mb-4 text-white')

                with ui.column().classes('gap-4 w-full max-w-2xl'):
                    # Connection status indicators
                    ui.label('Connection Status').classes('text-lg font-semibold text-white')
                    with ui.row().classes('gap-4 items-center'):
                        taapi_status = ui.label('TAAPI: 🔴 Not Connected').classes('text-sm')
                        hyperliquid_status = ui.label('Hyperliquid: 🔴 Not Connected').classes('text-sm')
                        openrouter_status = ui.label('OpenRouter: 🔴 Not Connected').classes('text-sm')

                    ui.separator()

                    # TAAPI Key
                    ui.label('TAAPI.io API Key').classes('text-lg font-semibold text-white')
                    taapi_input = ui.input(
                        label='TAAPI API Key',
                        placeholder='eyJhbGciOiJI...',
                        value=config_data['api_keys']['taapi_api_key'],
                        password=True,
                        password_toggle_button=True
                    ).classes('w-full')
                    ui.label('Get your API key from https://taapi.io').classes('text-xs text-gray-400')

                    ui.separator()

                    # Hyperliquid Key
                    ui.label('Hyperliquid Private Key').classes('text-lg font-semibold text-white')
                    hyperliquid_input = ui.input(
                        label='Private Key',
                        placeholder='0x...',
                        value=config_data['api_keys']['hyperliquid_private_key'],
                        password=True,
                        password_toggle_button=True
                    ).classes('w-full')
                    ui.label('Your wallet private key for trading').classes('text-xs text-gray-400')

                    # Network selection
                    hyperliquid_network = ui.select(
                        label='Network',
                        options=['mainnet', 'testnet'],
                        value=config_data['api_keys']['hyperliquid_network']
                    ).classes('w-full')

                    ui.separator()

                    # OpenRouter Key
                    ui.label('OpenRouter API Key').classes('text-lg font-semibold text-white')
                    openrouter_input = ui.input(
                        label='OpenRouter API Key',
                        placeholder='sk-or-v1-...',
                        value=config_data['api_keys']['openrouter_api_key'],
                        password=True,
                        password_toggle_button=True
                    ).classes('w-full')
                    ui.label('Get your API key from https://openrouter.ai').classes('text-xs text-gray-400')

                    ui.separator()

                    # Test connections button
                    async def test_api_connections():
                        """Test all API connections"""
                        try:
                            ui.notify('Testing API connections...', type='info')

                            # Update environment variables temporarily for testing
                            if taapi_input.value:
                                os.environ['TAAPI_API_KEY'] = taapi_input.value
                            if hyperliquid_input.value:
                                os.environ['HYPERLIQUID_PRIVATE_KEY'] = hyperliquid_input.value
                            if openrouter_input.value:
                                os.environ['OPENROUTER_API_KEY'] = openrouter_input.value

                            # Test connections via bot service
                            results = await bot_service.test_api_connections()

                            # Update status indicators
                            taapi_status.text = f"TAAPI: {'🟢 Connected' if results.get('TAAPI', False) else '🔴 Failed'}"
                            hyperliquid_status.text = f"Hyperliquid: {'🟢 Connected' if results.get('Hyperliquid', False) else '🔴 Failed'}"
                            openrouter_status.text = f"OpenRouter: {'🟢 Connected' if results.get('OpenRouter', False) else '🔴 Failed'}"

                            # Show summary notification
                            connected_count = sum(1 for v in results.values() if v)
                            total_count = len(results)

                            if connected_count == total_count:
                                ui.notify(f'All APIs connected successfully! ({connected_count}/{total_count})', type='positive')
                            elif connected_count > 0:
                                ui.notify(f'Partially connected: {connected_count}/{total_count} APIs', type='warning')
                            else:
                                ui.notify('All connections failed. Check your API keys.', type='negative')

                        except Exception as e:
                            ui.notify(f'Error testing connections: {str(e)}', type='negative')

                    async def save_api_keys():
                        """Save API keys to configuration"""
                        try:
                            # Update config data
                            config_data['api_keys']['taapi_api_key'] = taapi_input.value
                            config_data['api_keys']['hyperliquid_private_key'] = hyperliquid_input.value
                            config_data['api_keys']['hyperliquid_network'] = hyperliquid_network.value
                            config_data['api_keys']['openrouter_api_key'] = openrouter_input.value

                            # Save to file
                            if save_config(config_data):
                                # Update environment variables
                                if taapi_input.value:
                                    os.environ['TAAPI_API_KEY'] = taapi_input.value
                                if hyperliquid_input.value:
                                    os.environ['HYPERLIQUID_PRIVATE_KEY'] = hyperliquid_input.value
                                if openrouter_input.value:
                                    os.environ['OPENROUTER_API_KEY'] = openrouter_input.value

                                ui.notify('API keys saved successfully!', type='positive')
                                ui.notify('Note: Restart the bot for changes to take effect', type='info')
                            else:
                                ui.notify('Failed to save API keys', type='negative')
                        except Exception as e:
                            ui.notify(f'Error saving API keys: {str(e)}', type='negative')

                    with ui.row().classes('gap-2'):
                        ui.button('Save API Keys', on_click=save_api_keys, icon='save').props('color=primary')
                        ui.button('Test Connections', on_click=test_api_connections, icon='network_check').props('color=secondary')

                    ui.separator()

                    # Warning
                    with ui.card().classes('bg-orange-900 p-4'):
                        ui.label('⚠️ Security Warning').classes('text-lg font-bold text-white mb-2')
                        ui.label('Never share your private keys. Keys are stored in data/config.json - keep this file secure!').classes('text-sm text-gray-200')

            # ===== TAB 3: RISK MANAGEMENT =====
            with ui.tab_panel(tab_risk):
                ui.label('Risk Management').classes('text-2xl font-bold mb-4 text-white')

                with ui.column().classes('gap-6 w-full max-w-2xl'):
                    # Max Position Size
                    ui.label('Maximum Position Size').classes('text-lg font-semibold text-white')
                    with ui.row().classes('items-center w-full gap-4'):
                        max_position_slider = ui.slider(
                            min=100,
                            max=10000,
                            value=config_data['risk_management']['max_position_size'],
                            step=100
                        ).classes('flex-grow')
                        max_position_label = ui.label(f"${config_data['risk_management']['max_position_size']:,.0f}").classes('text-white font-bold min-w-[100px]')
                        max_position_slider.on('update:model-value', lambda e: max_position_label.set_text(f'${e.args:,.0f}'))
                    ui.label('Maximum USD allocation per position').classes('text-xs text-gray-400')

                    ui.separator()

                    # Max Leverage
                    ui.label('Maximum Leverage').classes('text-lg font-semibold text-white')
                    with ui.row().classes('items-center w-full gap-4'):
                        max_leverage_slider = ui.slider(
                            min=1,
                            max=20,
                            value=config_data['risk_management']['max_leverage'],
                            step=0.5
                        ).classes('flex-grow')
                        max_leverage_label = ui.label(f"{config_data['risk_management']['max_leverage']:.1f}x").classes('text-white font-bold min-w-[100px]')
                        max_leverage_slider.on('update:model-value', lambda e: max_leverage_label.set_text(f'{e.args:.1f}x'))
                    ui.label('Maximum leverage for perpetual futures (1x-20x)').classes('text-xs text-gray-400')

                    ui.separator()

                    # Stop Loss %
                    ui.label('Default Stop Loss').classes('text-lg font-semibold text-white')
                    with ui.row().classes('items-center w-full gap-4'):
                        stop_loss_slider = ui.slider(
                            min=1,
                            max=20,
                            value=config_data['risk_management']['stop_loss_pct'],
                            step=0.5
                        ).classes('flex-grow')
                        stop_loss_label = ui.label(f"{config_data['risk_management']['stop_loss_pct']:.1f}%").classes('text-white font-bold min-w-[100px]')
                        stop_loss_slider.on('update:model-value', lambda e: stop_loss_label.set_text(f'{e.args:.1f}%'))
                    ui.label('Default stop loss percentage from entry').classes('text-xs text-gray-400')

                    ui.separator()

                    # Take Profit %
                    ui.label('Default Take Profit').classes('text-lg font-semibold text-white')
                    with ui.row().classes('items-center w-full gap-4'):
                        take_profit_slider = ui.slider(
                            min=2,
                            max=50,
                            value=config_data['risk_management']['take_profit_pct'],
                            step=1
                        ).classes('flex-grow')
                        take_profit_label = ui.label(f"{config_data['risk_management']['take_profit_pct']:.0f}%").classes('text-white font-bold min-w-[100px]')
                        take_profit_slider.on('update:model-value', lambda e: take_profit_label.set_text(f'{e.args:.0f}%'))
                    ui.label('Default take profit percentage from entry').classes('text-xs text-gray-400')

                    ui.separator()

                    # Max Open Positions
                    ui.label('Maximum Open Positions').classes('text-lg font-semibold text-white')
                    max_positions_input = ui.number(
                        label='Max Positions',
                        value=config_data['risk_management']['max_open_positions'],
                        min=1,
                        max=20
                    ).classes('w-full')
                    ui.label('Maximum number of concurrent open positions').classes('text-xs text-gray-400')

                    ui.separator()

                    # Save button
                    async def save_risk_config():
                        try:
                            # Update config data
                            config_data['risk_management']['max_position_size'] = int(max_position_slider.value)
                            config_data['risk_management']['max_leverage'] = float(max_leverage_slider.value)
                            config_data['risk_management']['stop_loss_pct'] = float(stop_loss_slider.value)
                            config_data['risk_management']['take_profit_pct'] = float(take_profit_slider.value)
                            config_data['risk_management']['max_open_positions'] = int(max_positions_input.value)

                            # Save to file
                            if save_config(config_data):
                                ui.notify('Risk management settings saved successfully!', type='positive')
                            else:
                                ui.notify('Failed to save risk settings', type='negative')
                        except Exception as e:
                            ui.notify(f'Error saving risk config: {str(e)}', type='negative')

                    ui.button('Save Risk Settings', on_click=save_risk_config, icon='save').props('color=primary')

                    ui.separator()

                    # Warning about leverage
                    with ui.card().classes('bg-red-900 p-4'):
                        ui.label('⚠️ Risk Warning').classes('text-lg font-bold text-white mb-2')
                        ui.label('High leverage increases both potential profits and losses. Use with caution!').classes('text-sm text-gray-200')

            # ===== TAB 4: NOTIFICATIONS =====
            with ui.tab_panel(tab_notifications):
                ui.label('Notifications').classes('text-2xl font-bold mb-4 text-white')

                with ui.column().classes('gap-4 w-full max-w-2xl'):
                    # Desktop Notifications
                    ui.label('Desktop Notifications').classes('text-lg font-semibold text-white')
                    desktop_enabled_checkbox = ui.checkbox(
                        'Enable Desktop Notifications',
                        value=config_data['notifications']['desktop_enabled']
                    )
                    ui.label('Show system notifications for important events').classes('text-xs text-gray-400')

                    ui.separator()

                    # Telegram Bot
                    ui.label('Telegram Notifications').classes('text-lg font-semibold text-white')
                    telegram_enabled_checkbox = ui.checkbox(
                        'Enable Telegram Notifications',
                        value=config_data['notifications']['telegram_enabled']
                    )

                    # Telegram token and chat ID (shown when enabled)
                    telegram_token_input = ui.input(
                        label='Telegram Bot Token',
                        placeholder='123456:ABC-DEF...',
                        value=config_data['notifications']['telegram_token'],
                        password=True,
                        password_toggle_button=True
                    ).classes('w-full')
                    telegram_token_input.visible = telegram_enabled_checkbox.value

                    telegram_chat_input = ui.input(
                        label='Telegram Chat ID',
                        placeholder='123456789',
                        value=config_data['notifications']['telegram_chat_id']
                    ).classes('w-full')
                    telegram_chat_input.visible = telegram_enabled_checkbox.value

                    # Toggle visibility when checkbox changes
                    def toggle_telegram_inputs(e):
                        telegram_token_input.visible = e.value
                        telegram_chat_input.visible = e.value

                    telegram_enabled_checkbox.on('update:model-value', toggle_telegram_inputs)

                    ui.label('Get your bot token from @BotFather on Telegram').classes('text-xs text-gray-400')

                    ui.separator()

                    # Test Notification button
                    async def test_notification():
                        try:
                            if desktop_enabled_checkbox.value:
                                ui.notify('Test notification sent! This is how trade alerts will look.', type='info')
                            else:
                                ui.notify('Desktop notifications are disabled', type='warning')

                            if telegram_enabled_checkbox.value and telegram_token_input.value:
                                ui.notify('Telegram test notification would be sent here', type='info')
                                # TODO: Implement actual Telegram notification

                        except Exception as e:
                            ui.notify(f'Error sending test notification: {str(e)}', type='negative')

                    # Save button
                    async def save_notification_config():
                        try:
                            # Update config data
                            config_data['notifications']['desktop_enabled'] = desktop_enabled_checkbox.value
                            config_data['notifications']['telegram_enabled'] = telegram_enabled_checkbox.value
                            config_data['notifications']['telegram_token'] = telegram_token_input.value
                            config_data['notifications']['telegram_chat_id'] = telegram_chat_input.value

                            # Save to file
                            if save_config(config_data):
                                ui.notify('Notification settings saved successfully!', type='positive')
                            else:
                                ui.notify('Failed to save notification settings', type='negative')
                        except Exception as e:
                            ui.notify(f'Error saving notification config: {str(e)}', type='negative')

                    with ui.row().classes('gap-2'):
                        ui.button('Save Notification Settings', on_click=save_notification_config, icon='save').props('color=primary')
                        ui.button('Test Notification', on_click=test_notification, icon='notifications_active').props('color=secondary')

                    ui.separator()

                    # Info box
                    with ui.card().classes('bg-blue-900 p-4'):
                        ui.label('ℹ️ Notification Features').classes('text-lg font-bold text-white mb-2')
                        ui.label('Configure notifications for trade executions, errors, and daily summaries.').classes('text-sm text-gray-200')

    # Load current configuration on page load
    async def load_initial_config():
        """Load current bot configuration on page initialization"""
        try:
            current_config = await bot_service.get_current_config() if hasattr(bot_service, 'get_current_config') else None
            if current_config:
                # Update UI with current config
                pass
        except Exception as e:
            pass  # Fail silently on initial load

    # Schedule initial config load
    asyncio.create_task(load_initial_config())
