#gui/video_tools.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLineEdit, QLabel, QSpinBox, QTextEdit, QFileDialog,
                               QTabWidget, QCheckBox, QProgressBar, QComboBox, QSlider)
from PySide6.QtCore import Qt, QThread, Signal, QMutex, QWaitCondition
import subprocess
import os
import shutil
import time
from utils.file_naming import FileNamingUtils

class FrameExtractionThread(QThread):
    progress_update = Signal(str)
    progress_value = Signal(int)
    finished_signal = Signal(bool, str)
    
    def __init__(self, video_path, output_dir, fps=1):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.fps = fps
        self.process = None
        self._is_paused = False
        self._should_stop = False
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        
    def pause(self):
        self.mutex.lock()
        self._is_paused = True
        self.mutex.unlock()
        
    def resume(self):
        self.mutex.lock()
        self._is_paused = False
        self.pause_condition.wakeAll()
        self.mutex.unlock()
        
    def stop(self):
        self._should_stop = True
        if self.process:
            self.process.terminate()
        self.resume()  # Wake up if paused
        
    def run(self):
        try:
            # Create output directory
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', self.video_path,
                '-vf', f'fps={self.fps}',
                os.path.join(self.output_dir, 'frame_%06d.png'),
                '-hide_banner',
                '-loglevel', 'info'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in self.process.stdout:
                # Check if paused
                self.mutex.lock()
                while self._is_paused and not self._should_stop:
                    self.pause_condition.wait(self.mutex)
                self.mutex.unlock()
                
                # Check if should stop
                if self._should_stop:
                    self.process.terminate()
                    break
                    
                self.progress_update.emit(line.strip())
                
            self.process.wait()
            
            if self._should_stop:
                self.finished_signal.emit(False, "Frame extraction stopped by user")
            elif self.process.returncode == 0:
                frame_count = len([f for f in os.listdir(self.output_dir) if f.endswith('.png')])
                self.finished_signal.emit(True, f"Extracted {frame_count} frames successfully")
            else:
                self.finished_signal.emit(False, "Frame extraction failed")
                
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {str(e)}")

class VideoTrimThread(QThread):
    progress_update = Signal(str)
    finished_signal = Signal(bool, str)
    
    def __init__(self, input_path, output_path, start_time, end_time):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.start_time = start_time
        self.end_time = end_time
        self.process = None
        self._should_stop = False
        
    def stop(self):
        self._should_stop = True
        if self.process:
            self.process.terminate()
        
    def run(self):
        try:
            duration = self.end_time - self.start_time
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', self.input_path,
                '-ss', str(self.start_time),
                '-t', str(duration),
                '-c', 'copy',
                '-avoid_negative_ts', 'make_zero',
                self.output_path,
                '-y'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in self.process.stdout:
                if self._should_stop:
                    self.process.terminate()
                    break
                self.progress_update.emit(line.strip())
                
            self.process.wait()
            
            if self._should_stop:
                self.finished_signal.emit(False, "Video trimming stopped by user")
            elif self.process.returncode == 0:
                self.finished_signal.emit(True, f"Video trimmed successfully")
            else:
                self.finished_signal.emit(False, "Video trimming failed")
                
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {str(e)}")

class VideoTools(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.extraction_thread = None
        self.trim_thread = None
        self.is_extraction_paused = False
        self.setup_ui()
    # Add these helper methods to VideoTools class if they don't exist:

    def parse_time_string(self, time_str):
        """Convert HH:MM:SS or MM:SS or SS to seconds"""
        if not time_str:
            return 0
            
        try:
            parts = time_str.strip().split(':')
            if len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 1:  # SS
                return int(parts[0])
            else:
                return 0
        except:
            return 0
            
    def format_seconds_to_time(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"    
    def get_button_style(self, bg_color="#4a4a4a", hover_color="#5a5a5a"):
        return f"""
            QPushButton {{
                padding: 10px 20px;
                background-color: {bg_color};
                border: none;
                border-radius: 5px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #2a2a2a;
                color: #666666;
            }}
        """
        
    def on_mode_changed(self, index):
        """Handle extraction mode change"""
        # Show/hide relevant settings based on mode
        if index == 0:  # Fixed Interval (FPS)
            self.fps_widget.show()
            self.threshold_widget.hide()
        elif index == 1:  # Scene Detection
            self.fps_widget.hide()
            self.threshold_widget.show()
        else:  # Keyframes Only
            self.fps_widget.hide()
            self.threshold_widget.hide()
        
    def browse_frame_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video File",
            self.config.get_default_download_path(),
            "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.ts)"
        )
        if file_path:
            self.frame_video_input.setText(file_path)
            # Get video info and update FPS
            self.get_video_info(file_path)
            
    def get_video_info(self, video_path):
        """Get video information using ffprobe"""
        try:
            # Run ffprobe to get video info
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=r_frame_rate,width,height,duration',
                '-of', 'json',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                if 'streams' in data and len(data['streams']) > 0:
                    stream = data['streams'][0]
                    
                    # Parse frame rate
                    fps_str = stream.get('r_frame_rate', '0/1')
                    if '/' in fps_str:
                        num, den = map(int, fps_str.split('/'))
                        fps = num / den if den != 0 else 0
                    else:
                        fps = float(fps_str)
                    
                    # Get resolution
                    width = stream.get('width', 'N/A')
                    height = stream.get('height', 'N/A')
                    
                    # Display video info
                    info_text = f"📹 Video Info: {width}x{height} @ {fps:.2f} FPS"
                    self.video_info_label.setText(info_text)
                    self.video_info_label.show()
                    
                    # Set FPS spinner to video's FPS (rounded to nearest integer)
                    if fps > 0:
                        self.fps_spin.setValue(min(int(round(fps)), self.fps_spin.maximum()))
                        self.frame_output.append(f"✅ Auto-detected video FPS: {fps:.2f}")
                        self.frame_output.append(f"📌 Set extraction FPS to: {self.fps_spin.value()}")
                    
        except Exception as e:
            self.frame_output.append(f"⚠️ Could not detect video FPS: {str(e)}")
            self.video_info_label.hide()
            
    def browse_trim_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Video File",
            self.config.get_default_download_path(),
            "Video Files (*.mp4 *.avi *.mkv *.mov *.flv *.ts)"
        )
        if file_path:
            self.trim_video_input.setText(file_path)
            # Get video duration for trim tab
            self.get_trim_video_info(file_path)
            
    # Update the get_trim_video_info method to show duration in HH:MM:SS:

    def get_trim_video_info(self, video_path):
        """Get video duration for trim settings"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                # Show duration in HH:MM:SS format
                self.trim_output.append(f"📹 Video duration: {self.format_seconds_to_time(duration)} ({duration:.2f} seconds)")
                
        except Exception as e:
            self.trim_output.append(f"⚠️ Could not detect video duration: {str(e)}")
            
    def extract_frames(self):
        video_path = self.frame_video_input.text()
        if not video_path:
            self.frame_output.append("❌ Please select a video file")
            return

        # Get video name for folder naming
        video_name = os.path.basename(video_path)
        
        # Get extraction settings
        mode_index = self.mode_combo.currentIndex()
        mode_text = self.mode_combo.currentText()
        
        if mode_index == 0:  # Fixed Interval (FPS)
            fps = self.fps_spin.value()
            folder_name = FileNamingUtils.generate_frames_name(video_name, "frames", f"{fps}fps")
        elif mode_index == 1:  # Scene Detection
            threshold = self.threshold_slider.value() / 100.0
            folder_name = FileNamingUtils.generate_frames_name(video_name, "scene", f"{threshold:.2f}")
        else:  # Keyframes Only
            folder_name = FileNamingUtils.generate_frames_name(video_name, "keyframes", "")

        # Create default output directory
        base_path = self.config.get_frames_base_path()
        default_output_dir = os.path.join(base_path, folder_name)

        # Create the default directory first
        try:
            os.makedirs(default_output_dir, exist_ok=True)
            self.frame_output.append(f"📁 Created output directory: {folder_name}")
        except Exception as e:
            self.frame_output.append(f"⚠️ Could not create default directory: {str(e)}")
            # Fall back to user's home directory
            default_output_dir = os.path.expanduser("~")

        # Ask user if they want to use the default directory or choose a different one
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setWindowTitle("Output Directory")
        msg.setText(f"Frames will be extracted to:\n{default_output_dir}")
        msg.setInformativeText("Do you want to use this directory or choose a different one?")
        use_default_btn = msg.addButton("✅ Use Default", QMessageBox.AcceptRole)
        choose_different_btn = msg.addButton("📁 Choose Different", QMessageBox.RejectRole)
        cancel_btn = msg.addButton("❌ Cancel", QMessageBox.RejectRole)
        msg.exec()

        clicked_button = msg.clickedButton()
        if clicked_button == cancel_btn:
            return
        elif clicked_button == choose_different_btn:
            # Let user choose a different directory
            output_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory for Frames",
                os.path.dirname(default_output_dir)
            )
            if not output_dir:
                return
        else:
            # Use the default directory we already created
            output_dir = default_output_dir

        # Clear output
        self.frame_output.clear()
        self.frame_output.append(f"🎬 Starting frame extraction...")
        self.frame_output.append(f"📁 Output directory: {output_dir}")

        # Update button states
        self.extract_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        # Start extraction thread based on mode
        if mode_index == 0:  # Fixed Interval (FPS)
            fps = self.fps_spin.value()
            self.frame_output.append(f"📊 Extracting {fps} frames per second")
            self.extraction_thread = FrameExtractionThread(video_path, output_dir, fps)
        elif mode_index == 1:  # Scene Detection
            threshold = self.threshold_slider.value() / 100.0
            self.extraction_thread = SceneExtractionThread(video_path, output_dir, threshold)
        else:  # Keyframes Only
            self.extraction_thread = KeyframeExtractionThread(video_path, output_dir)

        self.extraction_thread.progress_update.connect(self.update_frame_progress)
        self.extraction_thread.finished_signal.connect(self.frame_extraction_finished)
        self.extraction_thread.start()
    def pause_extraction(self):
        if self.extraction_thread and self.extraction_thread.isRunning():
            if self.is_extraction_paused:
                self.extraction_thread.resume()
                self.pause_button.setText("⏸️ Pause")
                self.frame_output.append("▶️ Extraction resumed")
                self.is_extraction_paused = False
            else:
                self.extraction_thread.pause()
                self.pause_button.setText("▶️ Resume")
                self.frame_output.append("⏸️ Extraction paused")
                self.is_extraction_paused = True
                
    def stop_extraction(self):
        if self.extraction_thread and self.extraction_thread.isRunning():
            self.extraction_thread.stop()
            self.frame_output.append("⏹️ Stopping extraction...")
            
    def update_frame_progress(self, message):
        self.frame_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.frame_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def frame_extraction_finished(self, success, message):
        self.extract_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.is_extraction_paused = False
        self.pause_button.setText("⏸️ Pause")
        
        if success:
            self.frame_output.append(f"✅ {message}")
        else:
            self.frame_output.append(f"❌ {message}")
    def trim_video(self):
        video_path = self.trim_video_input.text()
        if not video_path:
            self.trim_output.append("❌ Please select a video file")
            return

        # Parse time inputs
        start_time_str = self.trim_start_input.text().strip()
        end_time_str = self.trim_end_input.text().strip()

        start_time = self.parse_time_string(start_time_str)
        end_time = self.parse_time_string(end_time_str)

        if start_time >= end_time:
            self.trim_output.append("❌ End time must be greater than start time")
            return

        # Get video name for output naming
        video_name = os.path.basename(video_path)
        
        # Generate output filename using new naming format
        output_format = os.path.splitext(video_path)[1][1:]  # Get extension without dot
        if not output_format:
            output_format = "mp4"
        
        filename = FileNamingUtils.generate_trim_name(
            video_name, 
            start_time_str, 
            end_time_str, 
            output_format
        )

        # Create Trims directory if it doesn't exist
        base_path = self.config.get_default_download_path()
        trims_dir = os.path.join(base_path, "Trims")
        os.makedirs(trims_dir, exist_ok=True)

        # Get output file path
        default_output_path = os.path.join(trims_dir, filename)
        
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Trimmed Video As",
            default_output_path,
            f"Video Files (*.{output_format} *.mp4 *.avi *.mkv *.mov)"
        )

        if not output_path:
            return

        # Clear output
        self.trim_output.clear()
        self.trim_output.append(f"✂️ Starting video trim...")
        self.trim_output.append(f"📁 Output file: {os.path.basename(output_path)}")
        self.trim_output.append(f"⏱️ Start time: {self.format_seconds_to_time(start_time)}")
        self.trim_output.append(f"⏱️ End time: {self.format_seconds_to_time(end_time)}")
        
        duration = end_time - start_time
        self.trim_output.append(f"⏱️ Duration: {self.format_seconds_to_time(duration)} ({duration} seconds)")

        # Disable button during trimming
        self.trim_button.setEnabled(False)
        self.stop_trim_button.setEnabled(True)

        # Start trim thread
        self.trim_thread = VideoTrimThread(video_path, output_path, start_time, end_time)
        self.trim_thread.progress_update.connect(self.update_trim_progress)
        self.trim_thread.finished_signal.connect(self.trim_finished)
        self.trim_thread.start()
        
    def stop_trim(self):
        if self.trim_thread and self.trim_thread.isRunning():
            self.trim_thread.stop()
            self.trim_output.append("⏹️ Stopping trim...")
            
    def update_trim_progress(self, message):
        self.trim_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.trim_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def trim_finished(self, success, message):
        self.trim_button.setEnabled(True)
        self.stop_trim_button.setEnabled(False)
        
        if success:
            self.trim_output.append(f"✅ {message}")
        else:
            self.trim_output.append(f"❌ {message}")
    def create_video_trim_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("✂️ Trim Video")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #9147ff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Video input
        video_layout = QHBoxLayout()
        video_label = QLabel("Video File:")
        video_label.setFixedWidth(100)
        
        self.trim_video_input = QLineEdit()
        self.trim_video_input.setPlaceholderText("Select video file...")
        self.trim_video_input.setReadOnly(True)
        self.trim_video_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                background-color: #3a3a3a;
                color: #ffffff;
            }
        """)
        
        self.trim_browse_btn = QPushButton("📁 Browse")
        self.trim_browse_btn.clicked.connect(self.browse_trim_video)
        self.trim_browse_btn.setStyleSheet(self.get_button_style())
        
        video_layout.addWidget(video_label)
        video_layout.addWidget(self.trim_video_input)
        video_layout.addWidget(self.trim_browse_btn)
        layout.addLayout(video_layout)
        
        # Time settings
        time_group = QWidget()
        time_group.setStyleSheet("""
            QWidget {
                background-color: #3a3a3a;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        time_layout = QVBoxLayout(time_group)
        
        # Start time (now using HH:MM:SS format)
        start_layout = QHBoxLayout()
        start_label = QLabel("Start Time:")
        start_label.setFixedWidth(150)
        
        self.trim_start_input = QLineEdit()
        self.trim_start_input.setPlaceholderText("HH:MM:SS")
        self.trim_start_input.setFixedWidth(100)
        self.trim_start_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                color: #ffffff;
                font-family: monospace;
            }
        """)
        
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.trim_start_input)
        start_layout.addStretch()
        time_layout.addLayout(start_layout)
        
        # End time (changed from seconds to HH:MM:SS)
        end_layout = QHBoxLayout()
        end_label = QLabel("End Time:")
        end_label.setFixedWidth(150)
        
        self.trim_end_input = QLineEdit()
        self.trim_end_input.setPlaceholderText("HH:MM:SS")
        self.trim_end_input.setFixedWidth(100)
        self.trim_end_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                color: #ffffff;
                font-family: monospace;
            }
        """)
        
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.trim_end_input)
        end_layout.addStretch()
        time_layout.addLayout(end_layout)
        
        layout.addWidget(time_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.trim_button = QPushButton("✂️ Trim Video")
        self.trim_button.clicked.connect(self.trim_video)
        self.trim_button.setStyleSheet(self.get_button_style("#9147ff", "#7c3aed"))
        
        self.stop_trim_button = QPushButton("⏹️ Stop")
        self.stop_trim_button.clicked.connect(self.stop_trim)
        self.stop_trim_button.setEnabled(False)
        self.stop_trim_button.setStyleSheet(self.get_button_style("#ff3b30", "#e6352b"))
        
        button_layout.addWidget(self.trim_button)
        button_layout.addWidget(self.stop_trim_button)
        layout.addLayout(button_layout)
        
        # Progress output
        self.trim_output = QTextEdit()
        self.trim_output.setReadOnly(True)
        self.trim_output.setMaximumHeight(150)
        self.trim_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                color: #00ff00;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.trim_output)
        
        layout.addStretch()
        return widget
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for different tools
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
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
        
        # Frame extraction tab
        self.frame_tab = self.create_frame_extraction_tab()
        self.tabs.addTab(self.frame_tab, "🖼️ Extract Frames")
        
        # Video trim tab
        self.trim_tab = self.create_video_trim_tab()
        self.tabs.addTab(self.trim_tab, "✂️ Trim Video")
        
        layout.addWidget(self.tabs)
        
    def create_frame_extraction_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("🖼️ Extract Frames from Video")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #9147ff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Video input
        video_layout = QHBoxLayout()
        video_label = QLabel("Video File:")
        video_label.setFixedWidth(100)
        
        self.frame_video_input = QLineEdit()
        self.frame_video_input.setPlaceholderText("Select video file...")
        self.frame_video_input.setReadOnly(True)
        self.frame_video_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                background-color: #3a3a3a;
                color: #ffffff;
            }
        """)
        
        self.frame_browse_btn = QPushButton("📁 Browse")
        self.frame_browse_btn.clicked.connect(self.browse_frame_video)
        self.frame_browse_btn.setStyleSheet(self.get_button_style())
        
        video_layout.addWidget(video_label)
        video_layout.addWidget(self.frame_video_input)
        video_layout.addWidget(self.frame_browse_btn)
        layout.addLayout(video_layout)
        
        # Video info display
        self.video_info_label = QLabel("")
        self.video_info_label.setStyleSheet("""
            QLabel {
                color: #9147ff;
                font-size: 14px;
                padding: 10px;
                background-color: #3a3a3a;
                border-radius: 5px;
                margin: 5px 0;
            }
        """)
        self.video_info_label.hide()
        layout.addWidget(self.video_info_label)
        
        # Extraction mode
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Extraction Mode:")
        mode_label.setFixedWidth(150)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Fixed Interval (FPS)",
            "Scene Detection",
            "Keyframes Only"
        ])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.mode_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
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
                margin-right: 5px;
            }
        """)
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # Settings container (will show different settings based on mode)
        self.settings_container = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_container)
        
        # FPS setting (for fixed interval mode)
        self.fps_widget = QWidget()
        fps_layout = QHBoxLayout(self.fps_widget)
        fps_label = QLabel("Frames per Second:")
        fps_label.setFixedWidth(150)
        
        self.fps_spin = QSpinBox()
        self.fps_spin.setMinimum(1)
        self.fps_spin.setMaximum(120)  # Increased max for high FPS videos
        self.fps_spin.setValue(1)
        self.fps_spin.setToolTip("Extract X frames per second from the video")
        self.fps_spin.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                color: #ffffff;
            }
        """)
        
        fps_layout.addWidget(fps_label)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addStretch()
        self.settings_layout.addWidget(self.fps_widget)
        
        # Scene threshold setting (for scene detection mode)
        self.threshold_widget = QWidget()
        threshold_layout = QHBoxLayout(self.threshold_widget)
        threshold_label = QLabel("Lower = More sensitive to change")
        threshold_label.setFixedWidth(200)
        
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(1)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(30)  # 0.3
        self.threshold_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #4a4a4a;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #9147ff;
                width: 20px;
                height: 20px;
                border-radius: 10px;
                margin: -6px 0;
            }
        """)
        
        self.threshold_value = QLabel("0.30")
        self.threshold_value.setFixedWidth(40)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_value.setText(f"{v/100:.2f}")
        )
        
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value)
        threshold_layout.addStretch()
        self.settings_layout.addWidget(self.threshold_widget)
        self.threshold_widget.hide()
        
        layout.addWidget(self.settings_container)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.extract_button = QPushButton("🖼️ Extract Frames")
        self.extract_button.clicked.connect(self.extract_frames)
        self.extract_button.setStyleSheet(self.get_button_style("#9147ff", "#7c3aed"))
        
        self.pause_button = QPushButton("⏸️ Pause")
        self.pause_button.clicked.connect(self.pause_extraction)
        self.pause_button.setEnabled(False)
        self.pause_button.setStyleSheet(self.get_button_style("#ff9500", "#e68600"))
        
        self.stop_button = QPushButton("⏹️ Stop")
        self.stop_button.clicked.connect(self.stop_extraction)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(self.get_button_style("#ff3b30", "#e6352b"))
        
        button_layout.addWidget(self.extract_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        # Progress output
        self.frame_output = QTextEdit()
        self.frame_output.setReadOnly(True)
        self.frame_output.setMaximumHeight(150)
        self.frame_output.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                color: #00ff00;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.frame_output)
        
        layout.addStretch()
        return widget
        
    # In video_tools.py, update the create_video_trim_tab method:



# Additional thread classes for scene detection and keyframe extraction
class SceneExtractionThread(QThread):
    progress_update = Signal(str)
    finished_signal = Signal(bool, str)
    
    def __init__(self, video_path, output_dir, threshold):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.threshold = threshold
        self.process = None
        self._is_paused = False
        self._should_stop = False
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        
    def pause(self):
        self.mutex.lock()
        self._is_paused = True
        self.mutex.unlock()
        
    def resume(self):
        self.mutex.lock()
        self._is_paused = False
        self.pause_condition.wakeAll()
        self.mutex.unlock()
        
    def stop(self):
        self._should_stop = True
        if self.process:
            self.process.terminate()
        self.resume()  # Wake up if paused
        
    def run(self):
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Use ffmpeg with scene detection filter
            cmd = [
                'ffmpeg',
                '-i', self.video_path,
                '-vf', f"select='gt(scene,{self.threshold})',showinfo",
                '-vsync', 'vfr',
                os.path.join(self.output_dir, 'scene_%06d.png'),
                '-hide_banner'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in self.process.stdout:
                # Check if paused
                self.mutex.lock()
                while self._is_paused and not self._should_stop:
                    self.pause_condition.wait(self.mutex)
                self.mutex.unlock()
                
                # Check if should stop
                if self._should_stop:
                    self.process.terminate()
                    break
                    
                self.progress_update.emit(line.strip())
                
            self.process.wait()
            
            if self._should_stop:
                self.finished_signal.emit(False, "Scene extraction stopped by user")
            elif self.process.returncode == 0:
                frame_count = len([f for f in os.listdir(self.output_dir) if f.endswith('.png')])
                self.finished_signal.emit(True, f"Extracted {frame_count} scene changes")
            else:
                self.finished_signal.emit(False, "Scene extraction failed")
                
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {str(e)}")


class KeyframeExtractionThread(QThread):
    progress_update = Signal(str)
    finished_signal = Signal(bool, str)
    
    def __init__(self, video_path, output_dir):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.process = None
        self._is_paused = False
        self._should_stop = False
        self.mutex = QMutex()
        self.pause_condition = QWaitCondition()
        
    def pause(self):
        self.mutex.lock()
        self._is_paused = True
        self.mutex.unlock()
        
    def resume(self):
        self.mutex.lock()
        self._is_paused = False
        self.pause_condition.wakeAll()
        self.mutex.unlock()
        
    def stop(self):
        self._should_stop = True
        if self.process:
            self.process.terminate()
        self.resume()  # Wake up if paused
        
    def run(self):
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Extract only keyframes (I-frames)
            cmd = [
                'ffmpeg',
                '-i', self.video_path,
                '-vf', "select='eq(pict_type,I)'",
                '-vsync', 'vfr',
                os.path.join(self.output_dir, 'keyframe_%06d.png'),
                '-hide_banner'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            for line in self.process.stdout:
                # Check if paused
                self.mutex.lock()
                while self._is_paused and not self._should_stop:
                    self.pause_condition.wait(self.mutex)
                self.mutex.unlock()
                
                # Check if should stop
                if self._should_stop:
                    self.process.terminate()
                    break
                    
                self.progress_update.emit(line.strip())
                
            self.process.wait()
            
            if self._should_stop:
                self.finished_signal.emit(False, "Keyframe extraction stopped by user")
            elif self.process.returncode == 0:
                frame_count = len([f for f in os.listdir(self.output_dir) if f.endswith('.png')])
                self.finished_signal.emit(True, f"Extracted {frame_count} keyframes")
            else:
                self.finished_signal.emit(False, "Keyframe extraction failed")
                
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {str(e)}")