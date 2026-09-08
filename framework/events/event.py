from typing import Callable


class EventManager:
    """
    Handles event registration and dispatching.
    """

    def __init__(self):
        self.listeners: dict[str, list[Callable]] = {}


    def subscribe(
        self,
        event_name: str,
        callback: Callable
    ) -> None:
        if event_name not in self.listeners:
            self.listeners[event_name] = []

        self.listeners[event_name].append(callback)


    def emit(
        self,
        event_name: str,
        data=None
    ) -> None:
        for callback in self.listeners.get(event_name, []):
            callback(data)