"""
Transaction FSM states
"""
from aiogram.fsm.state import State, StatesGroup

class TransactionStates(StatesGroup):
    """Transaction creation states"""
    selecting_type = State()
    entering_amount = State()
    entering_note = State()
    selecting_category = State()
    selecting_date = State()
    confirming = State()
    
    # Category creation
    waiting_for_category_name = State()
    waiting_for_category_icon = State()
    waiting_for_category_type = State()
    
    # Label creation
    waiting_for_label_name = State()
