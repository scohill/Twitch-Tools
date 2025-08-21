#gui/streamer_settings.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QCheckBox, QGroupBox,
                               QFormLayout)
from PySide6.QtCore import Qt

class StreamerSettingsDialog(QDialog):
    def __init__(self, streamer_name, config, parent=None):
        super().__init__(parent)
        self.streamer_name = streamer_name
        self.config = config
        self.settings = config.get_streamer_settings(streamer_name)
        
        self.setWindowTitle(f"Settings - {streamer_name}")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        # Apply dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #9147ff;
                border: 1px solid #9147ff;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #4a4a4a;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #6a6a6a;
            }
        """)
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Auto Actions Group
        auto_group = QGroupBox("Auto Actions")
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setSpacing(10)
        
        self.auto_download_checkbox = QCheckBox("Auto Download when live")
        self.auto_download_checkbox.setToolTip("Automatically start downloading when the streamer goes live")
        
        self.auto_clip_checkbox = QCheckBox("Auto Clip (buffer last 3 minutes)")
        self.auto_clip_checkbox.setToolTip("Automatically buffer the last 3 minutes of the stream for clipping")
        
        auto_layout.addWidget(self.auto_download_checkbox)
        auto_layout.addWidget(self.auto_clip_checkbox)
        
        # Quality Settings Group
        quality_group = QGroupBox("Download Settings")
        quality_layout = QFormLayout(quality_group)
        quality_layout.setSpacing(10)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "best", "worst", "720p60", "720p", "480p", "360p", "160p"
        ])
        self.quality_combo.setToolTip("Video quality for downloads")
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv", "flv", "ts"])
        self.format_combo.setToolTip("Output format for downloaded videos")
        
        quality_layout.addRow("Quality:", self.quality_combo)
        quality_layout.addRow("Format:", self.format_combo)
        
        # Path Info Group (Read-only display)
        path_group = QGroupBox("Save Locations (Fixed)")
        path_layout = QFormLayout(path_group)
        path_layout.setSpacing(10)
        
        vod_path = self.config.get_streamer_vod_path(self.streamer_name)
        clips_path = self.config.get_streamer_clips_path(self.streamer_name)
        
        vod_label = QLabel(vod_path)
        vod_label.setWordWrap(True)
        vod_label.setStyleSheet("color: #888888; font-size: 11px;")
        
        clips_label = QLabel(clips_path)
        clips_label.setWordWrap(True)
        clips_label.setStyleSheet("color: #888888; font-size: 11px;")
        
        path_layout.addRow("VODs:", vod_label)
        path_layout.addRow("Clips:", clips_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #9147ff;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        # Add all groups to main layout
        layout.addWidget(auto_group)
        layout.addWidget(quality_group)
        layout.addWidget(path_group)
        layout.addStretch()
        layout.addLayout(button_layout)
        
    def load_settings(self):
        """Load current settings into the UI"""
        # Auto actions
        self.auto_download_checkbox.setChecked(
            self.settings.get('auto_download', False)
        )
        self.auto_clip_checkbox.setChecked(
            self.settings.get('auto_clip', False)
        )
        
        # Quality settings
        quality = self.settings.get('quality', 'best')
        quality_index = self.quality_combo.findText(quality)
        if quality_index >= 0:
            self.quality_combo.setCurrentIndex(quality_index)
            
        format_type = self.settings.get('format', 'mp4')
        format_index = self.format_combo.findText(format_type)
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)
            
    def save_settings(self):
        """Save settings to config"""
        # Save auto actions
        self.config.update_streamer_setting(
            self.streamer_name, 
            'auto_download', 
            self.auto_download_checkbox.isChecked()
        )
        self.config.update_streamer_setting(
            self.streamer_name, 
            'auto_clip', 
            self.auto_clip_checkbox.isChecked()
        )
        
        # Save quality settings
        self.config.update_streamer_setting(
            self.streamer_name, 
            'quality', 
            self.quality_combo.currentText()
        )
        self.config.update_streamer_setting(
            self.streamer_name, 
            'format', 
            self.format_combo.currentText()
        )
        
        self.accept()