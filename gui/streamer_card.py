#gui/streamer_card.py
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                               QLabel, QCheckBox, QFrame, QFileDialog, QComboBox,
                               QMessageBox)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont
import os
from datetime import datetime
from utils.file_naming import FileNamingUtils

class StreamerCard(QFrame):
    remove_requested = Signal()
    
    def __init__(self, streamer_name, stream_manager, config):
        super().__init__()
        self.streamer_name = streamer_name
        self.stream_manager = stream_manager
        self.config = config
        self.is_live = False
        self.is_downloading = False
        self.is_clipping = False
        self.download_filename = None
        self.download_timestamp = None
        self._settings_loaded = False
        self._initial_status_checked = False
        self._auto_download_override = False
        
        self.clip_message_timer = QTimer()
        self.clip_message_timer.timeout.connect(self.revert_clip_message)
        self.clip_message_timer.setSingleShot(True)
        
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
        QFrame {
            background-color: #3a3a3a;
            border: 2px solid #4a4a4a;
            border-radius: 10px;
            padding: 12px;
        }
        QFrame:hover {
            border-color: #5a5a5a;
        }
        """)
        
        self.setMinimumSize(280, 220)
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        self.name_label = QLabel(f"📺 {self.streamer_name}")
        self.name_label.setFont(QFont("Arial", 13, QFont.Bold))
        
        self.status_label = QLabel("⚫ Offline")
        self.status_label.setStyleSheet("color: #888888; font-size: 12px;")
        
        self.settings_button = QPushButton("⚙️")
        self.settings_button.setFixedSize(32, 32)
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setStyleSheet(self.get_icon_button_style())
        
        self.remove_button = QPushButton("❌")
        self.remove_button.setFixedSize(32, 32)
        self.remove_button.clicked.connect(self.remove_requested.emit)
        self.remove_button.setStyleSheet(self.get_icon_button_style("#d32f2f"))
        
        header_layout.addWidget(self.name_label)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.settings_button)
        header_layout.addWidget(self.remove_button)
        
        main_layout.addLayout(header_layout)
        
        # Controls row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        
        self.auto_download_checkbox = QCheckBox("Auto DL")
        self.auto_download_checkbox.setToolTip("🎬 Auto Download when live")
        self.auto_download_checkbox.stateChanged.connect(self.on_auto_download_changed)
        self.auto_download_checkbox.setStyleSheet("font-size: 12px; padding: 2px;")
        
        self.auto_clip_checkbox = QCheckBox("Auto Clip")
        self.auto_clip_checkbox.setToolTip("✂️ Auto buffer last 3 minutes")
        self.auto_clip_checkbox.stateChanged.connect(self.on_auto_clip_changed)
        self.auto_clip_checkbox.setStyleSheet("font-size: 12px; padding: 2px;")
        
        controls_layout.addWidget(self.auto_download_checkbox)
        controls_layout.addWidget(self.auto_clip_checkbox)
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
        
        # Action buttons
        buttons_row1 = QHBoxLayout()
        buttons_row1.setSpacing(8)
        
        self.download_button = QPushButton("📥 Download")
        self.download_button.clicked.connect(self.toggle_download)
        self.download_button.setEnabled(False)
        self.download_button.setStyleSheet(self.get_compact_button_style())
        
        self.clip_button = QPushButton("💾 Clip")
        self.clip_button.clicked.connect(self.save_clip)
        self.clip_button.setEnabled(False)
        self.clip_button.setStyleSheet(self.get_compact_button_style())
        
        buttons_row1.addWidget(self.download_button)
        buttons_row1.addWidget(self.clip_button)
        
        buttons_row2 = QHBoxLayout()
        buttons_row2.setSpacing(8)
        
        self.vod_button = QPushButton("📁 VODs")
        self.vod_button.clicked.connect(self.open_vod_folder)
        self.vod_button.setStyleSheet(self.get_compact_button_style())
        
        self.clips_button = QPushButton("🎞️ Clips")
        self.clips_button.clicked.connect(self.open_clips_folder)
        self.clips_button.setStyleSheet(self.get_compact_button_style())
        
        buttons_row2.addWidget(self.vod_button)
        buttons_row2.addWidget(self.clips_button)
        
        main_layout.addLayout(buttons_row1)
        main_layout.addLayout(buttons_row2)
        
        # Info labels
        self.download_info_label = QLabel("")
        self.download_info_label.setWordWrap(True)
        self.download_info_label.setStyleSheet("color: #00ff00; font-size: 11px; padding: 4px;")
        self.download_info_label.setMinimumHeight(20)
        
        self.clip_info_label = QLabel("")
        self.clip_info_label.setWordWrap(True)
        self.clip_info_label.setStyleSheet("color: #00bfff; font-size: 11px; padding: 4px;")
        self.clip_info_label.setMinimumHeight(20)
        
        main_layout.addWidget(self.download_info_label)
        main_layout.addWidget(self.clip_info_label)
        
    def get_icon_button_style(self, hover_color="#5a5a5a"):
        return f"""
        QPushButton {{
            background-color: #4a4a4a;
            border: none;
            border-radius: 5px;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        """
        
    def get_compact_button_style(self):
        return """
        QPushButton {
            padding: 6px 12px;
            background-color: #4a4a4a;
            border: none;
            border-radius: 5px;
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
            min-height: 28px;
        }
        QPushButton:hover:enabled {
            background-color: #5a5a5a;
        }
        QPushButton:pressed:enabled {
            background-color: #6a6a6a;
        }
        QPushButton:disabled {
            background-color: #3a3a3a;
            color: #666666;
        }
        """
        
    def get_vod_path(self):
        """Get the hardcoded VODs directory path for this streamer"""
        vod_path = self.config.get_streamer_vod_path(self.streamer_name)
        os.makedirs(vod_path, exist_ok=True)
        return vod_path
        
    def get_clips_path(self):
        """Get the hardcoded Clips directory path for this streamer"""
        clips_path = self.config.get_streamer_clips_path(self.streamer_name)
        os.makedirs(clips_path, exist_ok=True)
        return clips_path
        
    def load_settings(self):
        settings = self.config.get_streamer_settings(self.streamer_name)
        
        self.auto_download_checkbox.blockSignals(True)
        self.auto_clip_checkbox.blockSignals(True)
        
        auto_download = settings.get('auto_download', False)
        auto_clip = settings.get('auto_clip', False)
        
        self.auto_download_checkbox.setChecked(auto_download)
        self.auto_clip_checkbox.setChecked(auto_clip)
        
        self.auto_download_checkbox.blockSignals(False)
        self.auto_clip_checkbox.blockSignals(False)
        
        self._settings_loaded = True
        
    def check_and_start_auto_actions(self):
        if self.is_live and self._settings_loaded:
            if self.auto_download_checkbox.isChecked() and not self.is_downloading and not self._auto_download_override:
                self.start_download()
            if self.auto_clip_checkbox.isChecked() and not self.is_clipping:
                self.start_clipping()
                
    def update_status(self, is_live):
        self.is_live = is_live
        self._initial_status_checked = True
        
        if is_live:
            self.status_label.setText("🔴 LIVE")
            self.status_label.setStyleSheet("color: #ff0000; font-weight: bold; font-size: 12px;")
            self.download_button.setEnabled(True)
            self.check_and_start_auto_actions()
        else:
            self.status_label.setText("⚫ Offline")
            self.status_label.setStyleSheet("color: #888888; font-size: 12px;")
            self.download_button.setEnabled(False)
            
            if self.is_downloading:
                self.stop_download(manual=False)
            if self.is_clipping:
                self.stop_clipping()
                
    def on_auto_download_changed(self, state):
        is_checked = (state == 2)
        self.config.update_streamer_setting(self.streamer_name, 'auto_download', is_checked)
        
        if is_checked:
            self._auto_download_override = False
            if self.is_live and not self.is_downloading:
                self.start_download()
        else:
            if self.is_downloading:
                self.stop_download(manual=False)
                
    def on_auto_clip_changed(self, state):
        is_checked = (state == 2)
        self.config.update_streamer_setting(self.streamer_name, 'auto_clip', is_checked)
        
        if is_checked and not self.is_clipping:
            if self._initial_status_checked and self.is_live:
                self.start_clipping()
            else:
                self.stream_manager.check_streamer_status(self.streamer_name)
        elif not is_checked and self.is_clipping:
            self.stop_clipping()
            
    def toggle_download(self):
        if self.is_downloading:
            self.stop_download(manual=True)
        else:
            self.start_download()
            
    def start_download(self):
        if not self.is_live:
            return
            
        self.is_downloading = True
        self.download_button.setText("⏹️ Stop")
        
        settings = self.config.get_streamer_settings(self.streamer_name)
        quality = settings.get('quality', 'best')
        output_format = settings.get('format', 'mp4')
        
        # Use the hardcoded VODs directory
        download_path = self.get_vod_path()
        
        # Generate filename using new naming format
        self.download_filename = FileNamingUtils.generate_live_vod_name(self.streamer_name, output_format)
        
        self.stream_manager.start_download(self.streamer_name, quality, output_format, download_path)
        
        timestamp_display = datetime.now().strftime("%H:%M")
        self.download_info_label.setText(f"📥 {timestamp_display} - {self.download_filename} - 0 MB")
        
    def stop_download(self, manual=False):
        self.is_downloading = False
        self.download_button.setText("📥 Download")
        
        if manual and self.auto_download_checkbox.isChecked():
            self._auto_download_override = True
            
        if self.download_filename and manual:
            vod_path = self.get_vod_path()
            full_path = os.path.join(vod_path, self.download_filename)
            print(vod_path)
            print(full_path)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("VOD Download Stopped")
            msg_box.setText(f"VOD saved as:\n{self.download_filename}")
            msg_box.setIcon(QMessageBox.Information)
            
            open_btn = msg_box.addButton("Open VOD", QMessageBox.ActionRole)
            folder_btn = msg_box.addButton("Open Folder", QMessageBox.ActionRole)
            msg_box.addButton(QMessageBox.Ok)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == open_btn:
                if os.path.exists(full_path):
                    if os.name == 'nt':
                        os.startfile(full_path)
                    elif os.name == 'posix':
                        os.system(f'open "{full_path}"')
            elif msg_box.clickedButton() == folder_btn:
                self.open_vod_folder()
                
        self.stream_manager.stop_download(self.streamer_name)
        self.download_info_label.setText("")
        self.download_filename = None
        self.download_timestamp = None
        
    def start_clipping(self):
        if not self.is_live:
            return
            
        self.is_clipping = True
        self.clip_button.setEnabled(True)
        
        self.stream_manager.start_clipping(self.streamer_name)
        self.clip_info_label.setText("✂️ Click \"Clip\" to Save the Latest 3 mins of the Stream")
        
    def stop_clipping(self):
        self.is_clipping = False
        self.clip_button.setEnabled(False)
        
        self.stream_manager.stop_clipping(self.streamer_name)
        self.clip_info_label.setText("")
        self.clip_message_timer.stop()
        
    def save_clip(self):
        if not self.is_clipping:
            return
            
        # Keep the original clip saving functionality - let stream_manager handle it
        clip_path = self.stream_manager.save_clip(self.streamer_name)
        
        if clip_path:
            self.clip_info_label.setText("✅ Saved!")
            clip_filename = os.path.basename(clip_path)
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Clip Saved")
            msg_box.setText(f"Clip saved as:\n{clip_filename}")
            msg_box.setIcon(QMessageBox.Information)
            
            open_btn = msg_box.addButton("Open Clip", QMessageBox.ActionRole)
            folder_btn = msg_box.addButton("Open Folder", QMessageBox.ActionRole)
            msg_box.addButton(QMessageBox.Ok)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == open_btn:
                if os.path.exists(clip_path):
                    if os.name == 'nt':
                        os.startfile(clip_path)
                    elif os.name == 'posix':
                        os.system(f'open "{clip_path}"')
            elif msg_box.clickedButton() == folder_btn:
                self.open_clips_folder()
                
            self.clip_message_timer.start(3000)
        else:
            self.clip_info_label.setText("❌ Failed")
            self.clip_message_timer.start(3000)
            
    def revert_clip_message(self):
        if self.is_clipping:
            self.clip_info_label.setText("✂️ Click \"Clip\" to Save the Latest 3 mins of the Stream")
            
    def open_vod_folder(self):
        """Open the VODs folder for this streamer"""
        vod_path = self.get_vod_path()
        
        if os.path.exists(vod_path):
            if os.name == 'nt':
                os.startfile(vod_path)
            elif os.name == 'posix':
                os.system(f'open "{vod_path}"')
                
    def open_clips_folder(self):
        """Open the Clips folder for this streamer"""
        clips_path = self.get_clips_path()
        
        if os.path.exists(clips_path):
            if os.name == 'nt':
                os.startfile(clips_path)
            elif os.name == 'posix':
                os.system(f'open "{clips_path}"')
                
    def show_settings(self):
        from gui.streamer_settings import StreamerSettingsDialog
        dialog = StreamerSettingsDialog(self.streamer_name, self.config, self)
        if dialog.exec():
            self.load_settings()
            
    def update_download_info(self, info):
        if self.is_downloading and self.download_filename:
            size = info.get('size', '0 MB')
            timestamp_display = datetime.now().strftime("%H:%M")
            self.download_info_label.setText(f"📥 {timestamp_display} - {self.download_filename} - {size}")