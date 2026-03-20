import pygame

from .states import MainMenuState, GameState, PauseState, SettingsState, GameplaySettingsState, DisplaySettingsState, AudioSettingsState, ConfirmChoiceState, BackgroundSelectionState
from core.state_registry import StateRegistry

class StateManager:
    def __init__(self, app):
        self.app = app
        self.stack = []
        self.pending_actions = []
    
    def process_changes(self):
        if not self.pending_actions:
            return

        while len(self.pending_actions) > 0:
            action, state_name, kwargs = self.pending_actions.pop(0)

            if action == "set":
                while self.stack:
                    state = self.stack.pop()
                    state.exit(**kwargs)
                state = StateRegistry.create(state_name, self.app, **kwargs)
                self.stack.append(state)
                #self.app.loop()
                #self.app.clock_tick()
                state.enter(**kwargs)
                
            elif action == "push":
                state = StateRegistry.create(state_name, self.app, **kwargs)
                self.stack.append(state)
                #self.app.loop()
                #self.app.clock_tick()
                state.enter(**kwargs)

            elif action == "pop" and self.stack:
                state = self.stack.pop()
                #self.app.loop()
                #self.app.clock_tick()
                state.exit(**kwargs)

            elif action == "clear":
                while self.stack:
                    state = self.stack.pop()
                    if "mute" in kwargs:
                        state.exit(**kwargs)
                    else:
                        state.exit(mute = True, **kwargs)

    def set_state(self, state_name, **kwargs):
        self.pending_actions.append(("set", state_name, kwargs))

    def push_state(self, state_name, **kwargs):
        self.pending_actions.append(("push", state_name, kwargs))
        
    def pop_state(self, **kwargs):
        self.pending_actions.append(("pop", None, kwargs))
            
    def clear_stack(self, **kwargs):
        self.pending_actions.append(("clear", None, kwargs))
                
    def current(self):
        return self.stack[-1] if self.stack else None
    
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
