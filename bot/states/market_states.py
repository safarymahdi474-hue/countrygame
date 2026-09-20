from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CreateListingStates(StatesGroup):
    waiting_offer_amount = State()
    waiting_request_amount = State()
