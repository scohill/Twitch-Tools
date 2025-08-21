#gui/main_window.py
from PySide6.QtWidgets import (QApplication,QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLineEdit, QScrollArea, QMessageBox,
                               QTabWidget, QLabel, QStyle)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
from gui.streamer_card import StreamerCard
from gui.help_dialog import HelpDialog
from gui.m3u8_downloader import M3U8Downloader
from gui.video_tools import VideoTools
import re
from PySide6.QtGui import QIcon
class MainWindow(QMainWindow):
    def __init__(self, stream_manager, config):
        super().__init__()
        self.setWindowIcon(QIcon("gui/logo.png"))
        self.stream_manager = stream_manager
        self.config = config
        self.streamer_cards = {}
        
        self.setWindowTitle("Twitch Tools 📺")
        self.setGeometry(300, 70, 900, 700)
        self.setMinimumSize(800, 700)

        # Apply dark theme
        self.apply_dark_theme()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4a4a4a;
            }
        """)
        
        # Create streamers tab
        self.streamers_widget = self.create_streamers_tab()
        self.tab_widget.addTab(self.streamers_widget, "📺 Streamers")
        
        # Create M3U8 downloader tab
        self.m3u8_widget = M3U8Downloader(self.config)
        self.tab_widget.addTab(self.m3u8_widget, "📥 Find/Download VOD")
        
        # Create video tools tab
        self.video_tools_widget = VideoTools(self.config)
        self.tab_widget.addTab(self.video_tools_widget, "🎬 Video Tools")
        
        main_layout.addWidget(self.tab_widget)
        
        # Load saved streamers
        self.load_streamers()
        
        # Connect stream manager signals
        self.stream_manager.status_updated.connect(self.update_streamer_status)
        self.stream_manager.download_progress.connect(self.update_download_progress)
        
    def create_streamers_tab(self):
        """Create the streamers tab with grid layout"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Header with compact design
        header_widget = QWidget()
        header_widget.setMaximumHeight(40)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        # Streamer input
        self.streamer_input = QLineEdit()
        self.streamer_input.setPlaceholderText("Add streamer name or Twitch URL...")
        self.streamer_input.returnPressed.connect(self.add_streamer)
        self.streamer_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                background-color: #2b2b2b;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #9147ff;
            }
        """)
        
        # Add button
        self.add_button = QPushButton("+ Add")
        self.add_button.clicked.connect(self.add_streamer)
        self.add_button.setFixedWidth(60)
        self.add_button.setStyleSheet("""
            QPushButton {
                padding: 6px;
                background-color: #9147ff;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        
        # Help button
        help_button = QPushButton("?")
        help_button.clicked.connect(self.show_help)
        help_button.setFixedSize(30, 30)
        help_button.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                border: none;
                border-radius: 15px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        """)
        
        header_layout.addWidget(self.streamer_input)
        header_layout.addWidget(self.add_button)
        header_layout.addWidget(help_button)
        
        layout.addWidget(header_widget)
        
        # Scrollable area for cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2b2b2b;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
        """)
        
        # Container for cards
        self.streamers_container = QWidget()
        self.streamers_container.setStyleSheet("background-color: transparent;")
        
        # Flow layout for responsive grid
        from gui.flow_layout import FlowLayout  # You'll need to create this
        self.streamers_layout = FlowLayout(self.streamers_container)
        self.streamers_layout.setSpacing(10)
        self.streamers_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.streamers_container)
        layout.addWidget(scroll_area)
        
        # Store cards
        self.streamer_cards = {}
        
        return widget
    def apply_dark_theme(self):
        """Apply a modern dark theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
    def extract_streamer_name(self, input_text):
        """Extract streamer name from URL or return the input if it's already a name"""
        # Remove whitespace
        input_text = input_text.strip()
        
        # Check if it's a URL
        url_patterns = [
            r'(?:https?://)?(?:www\.)?twitch\.tv/([a-zA-Z0-9_]+)',
            r'twitch\.tv/([a-zA-Z0-9_]+)',
            r'www\.twitch\.tv/([a-zA-Z0-9_]+)'
        ]
        
        for pattern in url_patterns:
            match = re.match(pattern, input_text)
            if match:
                return match.group(1)
        
        # If not a URL, return as is (assuming it's a username)
        return input_text
        
    def add_streamer(self):
        """Add a new streamer"""
        input_text = self.streamer_input.text().strip()
        if not input_text:
            return
            
        streamer_name = self.extract_streamer_name(input_text)
        
        # Check if already added
        if streamer_name.lower() in self.streamer_cards:
            # Flash the existing card
            card = self.streamer_cards[streamer_name.lower()]
            original_style = card.styleSheet()
            card.setStyleSheet(original_style.replace("#3a3a3a", "#5a5a5a"))
            QTimer.singleShot(200, lambda: card.setStyleSheet(original_style))
            return
            
        # Create new card
        card = StreamerCard(streamer_name, self.stream_manager, self.config)
        card.remove_requested.connect(lambda: self.remove_streamer(streamer_name))
        
        # Add to layout
        self.streamers_layout.addWidget(card)
        self.streamer_cards[streamer_name.lower()] = card
        
        # Save to config
        self.config.add_streamer(streamer_name)
        
        # Clear input
        self.streamer_input.clear()
        
        # Check initial status
        self.stream_manager.check_streamer_status(streamer_name)
        
    def remove_streamer(self, streamer_name):
        """Remove a streamer"""
        card = self.streamer_cards.get(streamer_name.lower())
        if card:
            # Animate removal
            card.setParent(None)
            card.deleteLater()
            
            # Remove from tracking
            del self.streamer_cards[streamer_name.lower()]
            
            # Stop any active operations
            self.stream_manager.stop_download(streamer_name)
            self.stream_manager.stop_clipping(streamer_name)
            
            # Remove from config
            self.config.remove_streamer(streamer_name)
            
    def load_streamers(self):
        """Load saved streamers from config"""
        for streamer_name in self.config.get_streamers():
            # Get the saved settings for this streamer
            settings = self.config.get_streamer_settings(streamer_name)
            
            card = StreamerCard(streamer_name, self.stream_manager, self.config)
            card.remove_requested.connect(lambda name=streamer_name: self.remove_streamer(name))
            
            self.streamers_layout.addWidget(card)
            self.streamer_cards[streamer_name.lower()] = card
            
            # Check initial status BEFORE loading settings
            # This will trigger update_status which sets is_live
            self.stream_manager.check_streamer_status(streamer_name) 
    def update_streamer_status(self, streamer_name, is_live):
        """Update streamer card status"""
        card = self.streamer_cards.get(streamer_name.lower())
        if card:
            card.update_status(is_live)
            
    def update_download_progress(self, streamer_name, info):
        """Update download progress information"""
        card = self.streamer_cards.get(streamer_name.lower())
        if card:
            card.update_download_info(info)
            
    def show_help(self):
        """Show help dialog"""
        dialog = HelpDialog(self)
        dialog.exec()
        
    def closeEvent(self, event):
        """Handle application close event"""
        self.stream_manager.stop_all_downloads()
        self.config.save()
        event.accept()