from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StatementStates(StatesGroup):
    waiting_title = State()
    waiting_body = State()
