import sys
import asyncio
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from qasync import QEventLoop
from reversi.protocol.interface import EngineInterface

class ReversiApp:
    def __init__(self, engine: EngineInterface, board_size: int = 8):
        self.engine = engine
        self.board_size = board_size
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle(f"Reversi {board_size}x{board_size} (PySide6)")
        self.window.resize(1000, 700)
        
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        self.label = QLabel("Reversi Migration in Progress...")
        layout.addWidget(self.label)
        self.window.setCentralWidget(central_widget)

    async def run(self):
        self.window.show()
        # Keep the event loop running
        while self.window.isVisible():
            await asyncio.sleep(0.1)

def run_app(engine: EngineInterface, board_size: int = 8):
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    reversi_app = ReversiApp(engine, board_size)
    
    with loop:
        loop.run_until_complete(reversi_app.run())
