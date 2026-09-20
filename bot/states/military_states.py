from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BuildUnitStates(StatesGroup):
    waiting_quantity = State()
