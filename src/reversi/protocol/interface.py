from abc import ABC, abstractmethod
from typing import Callable, Optional


class EngineInterface(ABC):
    """
    Abstract base class for Reversi Engine Interface.
    This decouples the UI from whether the engine is a local Python class
    or a remote process communicating via stdin/stdout.
    """

    def __init__(self):
        self.on_message: Optional[Callable[[str], None]] = None

    def set_callback(self, callback: Callable[[str], None]):
        """Set the callback function to handle messages from the engine."""
        self.on_message = callback

    @abstractmethod
    def start(self):
        """Start the engine process or thread."""
        pass

    @abstractmethod
    def send_command(self, command: str):
        """Send a text command to the engine."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the engine."""
        pass

    def _emit(self, message: str):
        """Helper to emit message to callback."""
        if self.on_message:
            self.on_message(message)
