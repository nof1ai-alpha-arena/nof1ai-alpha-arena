"""
Sidebar Component - Navigation menu
"""

from nicegui import ui


def create_sidebar():
    """Create sidebar navigation menu"""
    with ui.column().classes('w-64 bg-gray-800 p-4 gap-2 h-full'):
        # Navigation links
        menu_items = [
            ('/', '📊 Dashboard', 'Main dashboard with metrics and charts'),
            ('/positions', '💼 Positions', 'Active trading positions'),
            ('/history', '📜 History', 'Trade history and logs'),
            ('/market', '📈 Market', 'Market data and indicators'),
            ('/reasoning', '🧠 AI Reasoning', 'LLM decision logic'),
            ('/settings', '⚙️ Settings', 'Configuration and API keys'),
        ]

        for path, label, tooltip in menu_items:
            with ui.link(target=path).classes('no-underline w-full'):
                btn = ui.button(label).classes('w-full justify-start text-left')
                btn.props('flat')
                with btn:
                    ui.tooltip(tooltip)

        # Separator
        ui.separator().classes('my-4')

        # Version and info at bottom
        with ui.column().classes('mt-auto gap-1'):
            ui.label('Version 1.0.0').classes('text-xs text-gray-500 text-center')
            ui.label('Powered by NiceGUI').classes('text-xs text-gray-600 text-center')
