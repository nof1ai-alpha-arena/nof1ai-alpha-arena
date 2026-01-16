"""
Recommendations Page - AI trade proposals for manual approval
"""

from nicegui import ui
from src.gui.services.bot_service import BotService
from src.gui.services.state_manager import StateManager


def create_recommendations(bot_service: BotService, state_manager: StateManager):
    """Create recommendations page with pending AI proposals"""
    
    ui.label('🤖 AI Recommendations').classes('text-3xl font-bold mb-4 text-white')
    
    # Info banner
    with ui.card().classes('w-full p-4 mb-4 bg-blue-900 border-l-4 border-blue-500'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('info', size='24px').classes('text-blue-300')
            with ui.column().classes('gap-1'):
                ui.label('Manual Trading Mode').classes('text-lg font-bold text-white')
                ui.label('AI analyzes the market and proposes trades. Review and approve/reject each proposal.').classes('text-sm text-blue-200')
    
    # Container for proposals
    proposals_container = ui.column().classes('w-full gap-4')
    
    # Stats row
    stats_row = ui.row().classes('w-full gap-4 mb-4')
    
    async def update_proposals():
        """Update list of pending proposals"""
        state = state_manager.get_state()
        proposals = state.pending_proposals or []
        
        # Update stats
        stats_row.clear()
        with stats_row:
            # Total proposals
            with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-purple-800 to-purple-900'):
                ui.label(str(len(proposals))).classes('text-3xl font-bold text-white')
                ui.label('Pending Proposals').classes('text-sm text-purple-200 mt-1')
            
            # If bot is running
            if state.is_running:
                with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-green-800 to-green-900'):
                    ui.label('Active').classes('text-3xl font-bold text-white')
                    ui.label('Bot Status').classes('text-sm text-green-200 mt-1')
            else:
                with ui.card().classes('flex-1 p-4 bg-gradient-to-br from-gray-700 to-gray-800'):
                    ui.label('Stopped').classes('text-3xl font-bold text-white')
                    ui.label('Bot Status').classes('text-sm text-gray-300 mt-1')
        
        # Update proposals list
        proposals_container.clear()
        
        if not proposals:
            with proposals_container:
                with ui.card().classes('w-full p-8 bg-gradient-to-br from-gray-800 to-gray-900'):
                    with ui.column().classes('items-center gap-4'):
                        ui.icon('inbox', size='64px').classes('text-gray-600')
                        ui.label('No pending recommendations').classes('text-2xl text-gray-400')
                        ui.label('AI will create proposals when the bot analyzes the market.').classes('text-gray-500')
            return
        
        with proposals_container:
            for proposal in proposals:
                create_proposal_card(proposal)
    
    def create_proposal_card(proposal: dict):
        """Create a card for a single proposal"""
        asset = proposal.get('asset', 'N/A')
        action = proposal.get('action', 'hold')
        confidence = proposal.get('confidence', 0)
        entry_price = proposal.get('entry_price', 0)
        tp_price = proposal.get('tp_price')
        sl_price = proposal.get('sl_price')
        size = proposal.get('size', 0)
        allocation = proposal.get('allocation', 0)
        rationale = proposal.get('rationale', '')
        risk_reward = proposal.get('risk_reward')
        proposal_id = proposal.get('id', '')
        timestamp = proposal.get('timestamp', '')
        
        # Calculate potential gain/loss percentages
        potential_gain = proposal.get('potential_gain')
        potential_loss = proposal.get('potential_loss')
        
        # Determine card color based on action
        if action == 'buy':
            gradient = 'from-green-900 to-green-950'
            badge_color = 'bg-green-600'
            action_icon = '📈'
        elif action == 'sell':
            gradient = 'from-red-900 to-red-950'
            badge_color = 'bg-red-600'
            action_icon = '📉'
        else:
            gradient = 'from-gray-800 to-gray-900'
            badge_color = 'bg-gray-600'
            action_icon = '⏸'
        
        with ui.card().classes(f'w-full p-6 bg-gradient-to-br {gradient} border border-gray-700'):
            # Header row
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.label(action_icon).classes('text-4xl')
                    ui.label(asset).classes('text-3xl font-bold text-white')
                
                # Action badge
                with ui.badge().classes(f'{badge_color} text-white text-lg px-4 py-2'):
                    ui.label(action.upper())
            
            # Confidence bar
            with ui.row().classes('w-full items-center gap-3 mb-4'):
                ui.label('Confidence:').classes('text-sm text-gray-300')
                with ui.linear_progress(value=confidence / 100).classes('flex-1'):
                    pass
                ui.label(f'{confidence:.0f}%').classes('text-lg font-bold text-blue-400')
            
            # Trade details grid
            with ui.grid(columns=3).classes('w-full gap-4 mb-4'):
                # Entry Price
                with ui.card().classes('p-3 bg-gray-800 bg-opacity-50'):
                    ui.label('Entry Price').classes('text-xs text-gray-400 mb-1')
                    ui.label(f'${entry_price:,.2f}').classes('text-xl text-white font-bold')
                
                # Take Profit
                with ui.card().classes('p-3 bg-green-900 bg-opacity-30'):
                    ui.label('Take Profit').classes('text-xs text-gray-400 mb-1')
                    if tp_price:
                        ui.label(f'${tp_price:,.2f}').classes('text-xl text-green-400 font-bold')
                        if entry_price:
                            pct = ((tp_price - entry_price) / entry_price) * 100
                            ui.label(f'+{pct:.2f}%').classes('text-xs text-green-300')
                    else:
                        ui.label('N/A').classes('text-xl text-gray-500')
                
                # Stop Loss
                with ui.card().classes('p-3 bg-red-900 bg-opacity-30'):
                    ui.label('Stop Loss').classes('text-xs text-gray-400 mb-1')
                    if sl_price:
                        ui.label(f'${sl_price:,.2f}').classes('text-xl text-red-400 font-bold')
                        if entry_price:
                            pct = ((sl_price - entry_price) / entry_price) * 100
                            ui.label(f'{pct:.2f}%').classes('text-xs text-red-300')
                    else:
                        ui.label('N/A').classes('text-xl text-gray-500')
            
            # Size and allocation
            with ui.grid(columns=2).classes('w-full gap-4 mb-4'):
                with ui.card().classes('p-3 bg-gray-800 bg-opacity-50'):
                    ui.label('Position Size').classes('text-xs text-gray-400 mb-1')
                    ui.label(f'{size:.4f} {asset}').classes('text-lg text-white font-bold')
                
                with ui.card().classes('p-3 bg-gray-800 bg-opacity-50'):
                    ui.label('Allocation').classes('text-xs text-gray-400 mb-1')
                    ui.label(f'${allocation:,.2f}').classes('text-lg text-white font-bold')
            
            # Risk/Reward ratio
            if risk_reward:
                with ui.card().classes('w-full p-3 bg-blue-900 bg-opacity-30 mb-4'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('analytics', size='24px').classes('text-blue-400')
                        ui.label(f'Risk/Reward Ratio: 1:{risk_reward:.2f}').classes('text-lg text-blue-300 font-bold')
            
            # AI Rationale (expandable)
            with ui.expansion('🧠 AI Rationale', icon='psychology').classes('w-full bg-gray-800 bg-opacity-50 mb-4'):
                ui.label(rationale).classes('text-gray-300 whitespace-pre-wrap p-3')
            
            # Timestamp
            ui.label(f'Created: {timestamp[:19] if timestamp else "N/A"}').classes('text-xs text-gray-500 mb-4')
            
            # Action buttons
            with ui.row().classes('gap-3 w-full justify-end'):
                ui.button(
                    '❌ Reject',
                    on_click=lambda pid=proposal_id: reject_proposal(pid)
                ).classes('bg-red-600 hover:bg-red-700 text-white px-6 py-3 text-lg')
                
                ui.button(
                    '✅ Execute Trade',
                    on_click=lambda pid=proposal_id: approve_proposal(pid)
                ).classes('bg-green-600 hover:bg-green-700 text-white px-8 py-3 text-lg font-bold')
    
    async def approve_proposal(proposal_id: str):
        """Approve and execute a proposal"""
        try:
            success = bot_service.approve_proposal(proposal_id)
            if success:
                ui.notify('✅ Trade approved and executing!', type='positive', position='top')
                await update_proposals()
            else:
                ui.notify('❌ Failed to approve trade', type='negative')
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')
    
    async def reject_proposal(proposal_id: str):
        """Reject a proposal"""
        try:
            success = bot_service.reject_proposal(proposal_id, reason="Rejected by user via GUI")
            if success:
                ui.notify('❌ Proposal rejected', type='warning', position='top')
                await update_proposals()
            else:
                ui.notify('Failed to reject proposal', type='negative')
        except Exception as e:
            ui.notify(f'Error: {str(e)}', type='negative')
    
    # Auto-refresh every 2 seconds
    ui.timer(2.0, update_proposals)
    
    # Initial update
    # (timer will handle subsequent updates)
