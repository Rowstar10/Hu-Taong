import inspect

class StateRegistry:
    registry = {}

    @classmethod
    def register(cls, name, state_cls):
        cls.registry[name] = state_cls

    @classmethod
    def create(cls, name, app, **kwargs):
        if name not in cls.registry:
            raise ValueError(f"State '{name}' is not registered")
        spec = inspect.signature(cls.registry[name].__init__).parameters
        filtered = {k: v for k, v in kwargs.items() if k in spec}
        return cls.registry[name](app, **filtered)

    @classmethod
    def list_states(cls):
        return list(cls.registry.keys())

    def register_state(name):
        def decorator(cls):
            StateRegistry.register(name, cls)
            return cls
        return decorator
