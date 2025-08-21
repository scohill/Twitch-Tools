import sys
import signal
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QCoreApplication, QSocketNotifier
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow
from utils.config import Config
from utils.stream_manager import StreamManager
from utils.file_naming import FileNamingUtils
import traceback

def excepthook(type, value, tb):
    print("".join(traceback.format_exception(type, value, tb)))
    input("Press Enter to exit...")

sys.excepthook = excepthook

class TwitchMonitorApp:
    def __init__(self):
        # Set the working directory to the script's directory
        script_dir = Path(__file__).parent.absolute()
        os.chdir(script_dir)
        
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Twitch Monitor")
        self.app.setOrganizationName("TwitchMonitor")
        
        # Set application icon for taskbar (THIS IS THE KEY ADDITION)
        logo_path = Path("gui/logo.png")
        if logo_path.exists():
            app_icon = QIcon(str(logo_path))
            self.app.setWindowIcon(app_icon)  # This sets the taskbar icon
            
            # For Windows, also set the application user model ID for better taskbar integration
            if sys.platform == 'win32':
                try:
                    import ctypes
                    myappid = 'twitchmonitor.app.1.0'  # arbitrary string
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                except:
                    pass  # Ignore if this fails
        
        self.config = Config()
        self.stream_manager = StreamManager(self.config)
        self.main_window = MainWindow(self.stream_manager, self.config)
        
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_streamer_status)
        self.status_timer.start(5000)
        
        self.setup_signal_handlers()
        self.app.aboutToQuit.connect(self.cleanup)
    
    def setup_signal_handlers(self):
        if sys.platform != 'win32':
            self.signal_socket_pair = os.pipe()
            
            import fcntl
            flags = fcntl.fcntl(self.signal_socket_pair[1], fcntl.F_GETFL)
            fcntl.fcntl(self.signal_socket_pair[1], fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            self.signal_notifier = QSocketNotifier(self.signal_socket_pair[0], QSocketNotifier.Read)
            self.signal_notifier.activated.connect(self.handle_signal_notification)
            
            signal.signal(signal.SIGINT, self.unix_signal_handler)
            signal.signal(signal.SIGTERM, self.unix_signal_handler)
        else:
            signal.signal(signal.SIGINT, self.windows_signal_handler)
            
            self.interrupt_timer = QTimer()
            self.interrupt_timer.timeout.connect(lambda: None)
            self.interrupt_timer.start(100)
    
    def unix_signal_handler(self, signum, frame):
        try:
            os.write(self.signal_socket_pair[1], b'\x01')
        except:
            pass
    
    def windows_signal_handler(self, signum, frame):
        QTimer.singleShot(0, self.safe_quit)
    
    def handle_signal_notification(self):
        try:
            os.read(self.signal_socket_pair[0], 1)
        except:
            pass
        self.safe_quit()
    
    def safe_quit(self):
        QCoreApplication.quit()
        
    def check_streamer_status(self):
        try:
            self.stream_manager.check_all_streamers()
        except Exception:
            pass
        
    def cleanup(self):
        try:
            if hasattr(self, 'status_timer'):
                self.status_timer.stop()
                
            if hasattr(self, 'stream_manager'):
                self.stream_manager.stop_all_downloads()
                
                import time
                time.sleep(0.5)
                
            if hasattr(self, 'config'):
                self.config.save()
            
            if hasattr(self, 'signal_notifier'):
                self.signal_notifier.setEnabled(False)
            if hasattr(self, 'signal_socket_pair'):
                try:
                    os.close(self.signal_socket_pair[0])
                    os.close(self.signal_socket_pair[1])
                except:
                    pass
        except Exception:
            pass
            
    def run(self):
        self.main_window.show()
        return self.app.exec()

def main():
    app = TwitchMonitorApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()