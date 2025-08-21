#gui/help_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea, QWidget
from PySide6.QtCore import Qt

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help - Twitch Tools")
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                padding: 5px;
            }
            QPushButton {
                padding: 10px;
                background-color: #9147ff;
                border: none;
                border-radius: 5px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Create scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Title
        title = QLabel("📚 Twitch Tools Help")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        content_layout.addWidget(title)
        
        # Help sections
        help_sections = [
            ("🎮 Adding Streamers", 
             "• Enter a streamer's name or Twitch URL\n"
             "• Supported formats: shroud, twitch.tv/shroud, https://www.twitch.tv/shroud\n"
             "• Press Enter or click 'Add Streamer' button"),
            
            ("📺 Streamer Card", 
             "• Shows streamer name and live status (🔴 LIVE or ⚫ Offline)\n"
             "• Live status updates automatically every 30 seconds"),
            
            ("🎬 Auto Download", 
             "• Toggle to automatically start downloading when streamer goes live\n"
             "• Downloads continue until stream ends or manually stopped\n"
             "• Files saved with timestamp in filename"),
            
            ("✂️ Auto Clip", 
             "• Toggle to buffer the last 3 minutes of the stream\n"
             "• Continuously updates the buffer while stream is live\n"
             "• Click 'Save Clip' to save the buffered content"),
            
            ("📥 Download Button", 
             "• Manually start/stop downloading the stream\n"
             "• Only enabled when streamer is live\n"
             "• Shows download progress and speed"),
            
            ("💾 Save Clip Button", 
             "• Saves the last 3 minutes of buffered stream\n"
             "• Only enabled when Auto Clip is active\n"
             "• Clips saved with timestamp in filename"),
            
            ("📁 VODs Button", 
             "• Opens the folder containing downloaded streams\n"
             "• Each streamer can have custom download location"),
            
            ("🎞️ Clips Button", 
             "• Opens the folder containing saved clips\n"
             "• Each streamer can have custom clips location"),
            
            ("⚙️ Settings Button", 
             "• Configure quality, format, and save locations\n"
             "• Available qualities: best, source, 720p, 480p, etc.\n"
             "• Formats: mp4, ts"),
            
            ("❌ Remove Button", 
             "• Removes streamer from monitoring\n"
             "• Stops any active downloads or clips"),
            
            ("📥 VOD Find/Download Tab", 
             "• Find VODs \n"
             "• Watch/Download the VOD through the .m3u8 file\n"
             "• Download VODs from M3U8 URL\n"
             "• Play in VLC before downloading\n"
             "• Trim and download specific portions"),

            ("🎬 Video Tools Tab", 
             "• Extract frames from videos\n"
             "• Trim videos to specific time ranges\n"
             "• Various video processing utilities")
        ]
        
        for section_title, section_text in help_sections:
            # Section title
            title_label = QLabel(section_title)
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #9147ff;")
            content_layout.addWidget(title_label)
            
            # Section content
            content_label = QLabel(section_text)
            content_label.setWordWrap(True)
            content_label.setStyleSheet("margin-left: 20px; margin-bottom: 10px;")
            content_layout.addWidget(content_label)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)