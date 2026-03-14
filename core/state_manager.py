from .states import MainMenuState, GameState, PauseState, SettingsState, GameplaySettingsState, DisplaySettingsState, AudioSettingsState, ConfirmChoiceState, BackgroundSelectionState
from core.state_registry import StateRegistry

class StateManager:
    def __init__(self, app):
        self.app = app
        self.stack = []

    def current(self):
        return self.stack[-1] if self.stack else None

    def set_state(self, state_name, **kwargs):
        self.clear_stack(**kwargs)
        state = StateRegistry.create(state_name, self.app, **kwargs)
        self.stack.append(state)
        state.enter(**kwargs)

    def push_state(self, state_name, **kwargs):
        state = StateRegistry.create(state_name, self.app, **kwargs)
        self.stack.append(state)
        state.enter(**kwargs)

    def pop_state(self, **kwargs):
        if self.stack:
            state = self.stack.pop()
            state.exit(**kwargs)
            
    def clear_stack(self, **kwargs):
        while self.stack:
            state = self.stack.pop()
            if "mute" in kwargs:
                state.exit(**kwargs)
            else:
                state.exit(mute = True, **kwargs)

    def get_state(self, state_type):
        for state in reversed(self.stack):
            if isinstance(state, state_type):
                return state
        return None

    def update(self, dt):
        if self.stack:
            self.stack[-1].update(dt)

    def handle_event(self, event):
        if self.stack:
            self.stack[-1].handle_event(event)

    def draw(self, screen):
        if self.stack:
            self.stack[-1].draw(screen)
