"""
AI Trading Bot - NiceGUI Desktop Application
Entry point for the application
"""

import signal
import sys
import asyncio
import atexit
from nicegui import ui, app

# Global reference to bot_service for cleanup
bot_service_ref = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print("\n[INFO] Shutting down gracefully...")
    cleanup()
    sys.exit(0)

def cleanup():
    """Cleanup function called on exit"""
    global bot_service_ref
    if bot_service_ref and bot_service_ref.is_running():
        print("[INFO] Stopping bot engine...")
        try:
            # Run the async stop in a new event loop if needed
            try:
                loop = asyncio.get_running_loop()
                # If we're here, we're in an async context
                asyncio.create_task(bot_service_ref.stop())
            except RuntimeError:
                # No running loop, create one
                asyncio.run(bot_service_ref.stop())
            print("[INFO] Bot stopped successfully")
        except Exception as e:
            print(f"[WARN] Error stopping bot: {e}")

if __name__ in {"__main__", "__mp_main__"}:
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register cleanup on exit
    atexit.register(cleanup)

    # Import and setup app on startup
    from src.gui.app import create_app, bot_service

    # Save reference to bot_service for cleanup
    bot_service_ref = bot_service

    # Call create_app to register all pages
    create_app()

    # Register shutdown handler with NiceGUI app
    async def on_app_shutdown():
        """Called when NiceGUI app is shutting down"""
        print("[INFO] NiceGUI app shutdown event triggered")
        cleanup()

    app.on_shutdown(on_app_shutdown)

    # Run in native desktop mode
    ui.run(
        native=True,              # Desktop mode via pywebview
        window_size=(1400, 900),  # Window dimensions
        fullscreen=False,
        title="AI Trading Bot",
        favicon="🤖",
        dark=True,                # Dark theme
        reload=False,             # Disable hot reload in production
        show=True,                # Show window immediately
        port=8080,                # Default port
        binding_refresh_interval=0.1  # Faster UI updates
    )
