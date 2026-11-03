import pygame, pkgutil, importlib, inspect

class StateManager:
    registry = {}
    
    def __init__(self, app):
        self.app = app
        self.stack = []
        self.pending_actions = []

    @classmethod
    def register(cls, name, state_cls):
        if name in cls.registry:
            raise ValueError(f"State '{name}' is already registered")
        cls.registry[name] = state_cls

    @classmethod
    def create(cls, name, app, **kwargs):
        if name not in cls.registry:
            raise ValueError(f"State '{name}' is not registered")
        spec = inspect.signature(cls.registry[name].__init__).parameters
        filtered = {k: v for k, v in kwargs.items() if k in spec}
        return cls.registry[name](app, **filtered)
    
    def process_changes(self):
        if not self.pending_actions:
            return

        before = self.stack[self.screen_index()] if self.stack else None

        while len(self.pending_actions) > 0:
            action, state_name, kwargs = self.pending_actions.pop(0)

            if action == "set":
                while self.stack:
                    state = self.stack.pop()
                    state.exit(**kwargs)
                state = StateManager.create(state_name, self.app, **kwargs)
                self.stack.append(state)
                state.enter(**kwargs)
                
            elif action == "push":
                state = StateManager.create(state_name, self.app, **kwargs)
                self.stack.append(state)
                state.enter(**kwargs)

            elif action == "pop" and self.stack:
                state = self.stack.pop()
                state.exit(**kwargs)

            elif action == "clear":
                while self.stack:
                    state = self.stack.pop()
                    if "mute" in kwargs:
                        state.exit(**kwargs)
                    else:
                        state.exit(mute = True, **kwargs)
                        
        current_state = self.current()
        if getattr(current_state, "background_img", None):
            self.app.bg_current = self.app.background_cache[current_state.background_img]

        if self.stack and self.stack[self.screen_index()] is not before:
            self.app.fx.fade()

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

    def screen_index(self):
        # An overlay shows what is behind it, down to the nearest full screen
        first = len(self.stack) - 1
        while first > 0 and self.stack[first].is_overlay:
            first -= 1
        return first
    
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

    @classmethod
    def auto_register(cls, package_name, base_class):
        package = importlib.import_module(package_name)

        for module_info in pkgutil.iter_modules(package.__path__):
            module_name = module_info.name

            if module_name.startswith("_") or module_name == "base_state":
                continue

            module = importlib.import_module(f"{package_name}.{module_name}")

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (not issubclass(obj, base_class)
                    or not getattr(obj, "REGISTER", False)
                    or obj is base_class
                    or obj.__module__ != module.__name__):
                    continue

                state_name = getattr(obj, "NAME", None)

                if state_name is None:
                    raise ValueError(f"{obj.__name__} must define NAME = 'your_state_name'")

                cls.register(state_name, obj)
                print(f"[StateManager] Registered '{state_name}' -> {obj.__name__}")
