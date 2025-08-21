#utils/stream_manager.py
import subprocess
import threading
import time
import os
import sys
import glob
import shutil
import tempfile
from datetime import datetime
from PySide6.QtCore import QObject, Signal
from utils.file_naming import FileNamingUtils

class StreamManager(QObject):
    status_updated = Signal(str, bool)
    download_progress = Signal(str, dict)
    
    SEGMENT_DURATION = 10
    ROLLING_CLIP_SECONDS = 180
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.active_downloads = {}
        self.active_clips = {}
        self.clip_buffers = {}
        self.offline_confirmations = {}  # Track consecutive offline checks
        self.OFFLINE_CONFIRMATIONS_NEEDED = 3  # Require 3 consecutive offline checks
        self.last_known_status = {}  # Track last known status for each streamer
        
    def check_streamer_status(self, streamer_name):
        def check():
            try:
                result = subprocess.run(
                    ['streamlink', '--json', f'twitch.tv/{streamer_name}'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                
                is_live = result.returncode == 0 and 'streams' in result.stdout
                
                # Handle status with confirmation logic
                self._handle_status_update(streamer_name, is_live)
                
            except Exception:
                # On error, don't immediately mark as offline
                # Only update if we have no active downloads/clips
                if streamer_name not in self.active_downloads and streamer_name not in self.active_clips:
                    self.status_updated.emit(streamer_name, False)
                
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
        
    def stop_all_downloads(self, force=False):
        """Stop all active downloads and clips
        
        Args:
            force: If True, stop immediately without confirmation checks
        """
        # Stop all downloads
        for streamer_name in list(self.active_downloads.keys()):
            if force:
                # Force stop without confirmation
                self.stop_download(streamer_name)
            else:
                # Normal stop (would respect confirmation logic if implemented in stop_download)
                self.stop_download(streamer_name)
        
        # Stop all clips
        for streamer_name in list(self.active_clips.keys()):
            self.stop_clipping(streamer_name)
        
        # Clear confirmation tracking if force stopping
        if force:
            self.offline_confirmations.clear()
            self.last_known_status.clear()
            
    def _handle_status_update(self, streamer_name, is_live):
        """Handle status update with confirmation logic"""
        last_status = self.last_known_status.get(streamer_name, False)
        
        if is_live:
            # Stream is live - reset offline confirmations and update immediately
            self.offline_confirmations[streamer_name] = 0
            self.last_known_status[streamer_name] = True
            self.status_updated.emit(streamer_name, True)
            
        else:
            # Stream appears offline
            if last_status and (streamer_name in self.active_downloads or streamer_name in self.active_clips):
                # Was live and has active downloads/clips - need confirmations
                self.offline_confirmations[streamer_name] = self.offline_confirmations.get(streamer_name, 0) + 1
                
                if self.offline_confirmations[streamer_name] >= self.OFFLINE_CONFIRMATIONS_NEEDED:
                    # Confirmed offline after multiple checks
                    print(f"Stream {streamer_name} confirmed offline after {self.OFFLINE_CONFIRMATIONS_NEEDED} checks")
                    self.last_known_status[streamer_name] = False
                    self.status_updated.emit(streamer_name, False)
                    self.offline_confirmations[streamer_name] = 0
                else:
                    # Not enough confirmations yet - keep as live
                    print(f"Stream {streamer_name} appears offline ({self.offline_confirmations[streamer_name]}/{self.OFFLINE_CONFIRMATIONS_NEEDED} confirmations)")
                    # Don't emit status update - keep current status
            else:
                # No active downloads/clips or wasn't live before - update immediately
                self.last_known_status[streamer_name] = False
                self.status_updated.emit(streamer_name, False)
                self.offline_confirmations[streamer_name] = 0    
                
    def check_all_streamers(self):
        for streamer_name in self.config.get_streamers():
            self.check_streamer_status(streamer_name)
            
    def start_download(self, streamer_name, quality, output_format, download_path):
        if streamer_name in self.active_downloads:
            return
            
        # Use hardcoded path structure - ignore the passed download_path
        vod_path = self.config.get_streamer_vod_path(streamer_name)
        os.makedirs(vod_path, exist_ok=True)
        
        # Use new naming format for live VODs
        filename = FileNamingUtils.generate_live_vod_name(streamer_name, output_format)
        output_file = os.path.join(vod_path, filename)
        
        cmd = [
            'streamlink',
            f'twitch.tv/{streamer_name}',
            quality,
            '-o', output_file,
            '--twitch-disable-ads',
            '--twitch-low-latency',
            '--hls-live-restart',
            '--retry-streams', '30',
            '--retry-max', '10'
        ]
        
        if sys.platform == "win32":
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
        
        self.active_downloads[streamer_name] = {
            'process': process,
            'output_file': output_file,
            'start_time': datetime.now(),
            'filename': filename  # Store filename for UI display
        }
        
        thread = threading.Thread(
            target=self._monitor_download,
            args=(streamer_name, process),
            daemon=True
        )
        thread.start()

    def _monitor_download(self, streamer_name, process):
        try:
            download_info = self.active_downloads.get(streamer_name)
            if not download_info:
                return
                
            output_file = download_info['output_file']
            
            def monitor_file_size():
                last_size = 0
                last_time = time.time()
                
                while streamer_name in self.active_downloads and process.poll() is None:
                    try:
                        if os.path.exists(output_file):
                            file_size_bytes = os.path.getsize(output_file)
                            
                            if file_size_bytes < 1024:
                                size_str = f"{file_size_bytes} B"
                            elif file_size_bytes < 1024 * 1024:
                                size_str = f"{file_size_bytes / 1024:.1f} KB"
                            elif file_size_bytes < 1024 * 1024 * 1024:
                                size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
                            else:
                                size_str = f"{file_size_bytes / (1024 * 1024 * 1024):.2f} GB"
                            
                            current_time = time.time()
                            time_diff = current_time - last_time
                            if time_diff >= 1:
                                size_diff = file_size_bytes - last_size
                                speed_bytes = size_diff / time_diff
                                
                                if speed_bytes < 1024:
                                    speed_str = f"{speed_bytes:.0f} B/s"
                                elif speed_bytes < 1024 * 1024:
                                    speed_str = f"{speed_bytes / 1024:.1f} KB/s"
                                else:
                                    speed_str = f"{speed_bytes / (1024 * 1024):.1f} MB/s"
                                
                                last_size = file_size_bytes
                                last_time = current_time
                                
                                info = {
                                    'size': size_str,
                                    'speed': speed_str,
                                    'filename': download_info.get('filename', '')
                                }
                            else:
                                info = {
                                    'size': size_str,
                                    'filename': download_info.get('filename', '')
                                }
                                
                            self.download_progress.emit(streamer_name, info)
                            
                    except Exception:
                        pass
                    
                    time.sleep(1)
            
            size_thread = threading.Thread(target=monitor_file_size, daemon=True)
            size_thread.start()
            
            for line in process.stdout:
                if streamer_name not in self.active_downloads:
                    break
                    
        except Exception:
            pass

    def stop_download(self, streamer_name):
        if streamer_name in self.active_downloads:
            download_info = self.active_downloads[streamer_name]
            process = download_info['process']
            
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                
            del self.active_downloads[streamer_name]
            
    def start_clipping(self, streamer_name):
        if streamer_name in self.active_clips:
            return
            
        temp_dir = tempfile.mkdtemp(prefix=f"twitch_clip_{streamer_name}_")
        
        self.clip_buffers[streamer_name] = {
            'temp_dir': temp_dir,
            'stop_flag': threading.Event(),
            'stream_process': None,
            'segmenter_process': None,
            'is_running': True,
            'start_time': datetime.now()  # Track when clipping started
        }
        
        for f_path in glob.glob(os.path.join(temp_dir, "*.ts")):
            try:
                os.remove(f_path)
            except Exception:
                pass
        
        thread = threading.Thread(
            target=self._clip_recording_loop,
            args=(streamer_name,),
            daemon=True
        )
        thread.start()
        
        self.active_clips[streamer_name] = thread
        
    def _clip_recording_loop(self, streamer_name):
        buffer_info = self.clip_buffers[streamer_name]
        temp_dir = buffer_info['temp_dir']
        stop_flag = buffer_info['stop_flag']
        
        stream_url = f"https://twitch.tv/{streamer_name}"
        segment_pattern = os.path.join(temp_dir, "segment_%05d.ts")
        max_segments = self.ROLLING_CLIP_SECONDS // self.SEGMENT_DURATION
        
        stream_cmd = [
            "streamlink", 
            "--twitch-disable-ads", 
            "--twitch-low-latency",
            "--stdout", 
            stream_url, 
            "best"
        ]
        
        ffmpeg_cmd = [
            "ffmpeg", 
            "-y", 
            "-hide_banner", 
            "-loglevel", "error",
            "-i", "pipe:0", 
            "-c", "copy", 
            "-f", "segment",
            "-segment_time", str(self.SEGMENT_DURATION),
            "-reset_timestamps", "1", 
            segment_pattern
        ]
        
        stream_proc = None
        segmenter_proc = None
        
        try:
            if sys.platform == "win32":
                stream_proc = subprocess.Popen(
                    stream_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.DEVNULL, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                stream_proc = subprocess.Popen(
                    stream_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.DEVNULL
                )
            
            buffer_info['stream_process'] = stream_proc
            
            if sys.platform == "win32":
                segmenter_proc = subprocess.Popen(
                    ffmpeg_cmd, 
                    stdin=stream_proc.stdout, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                segmenter_proc = subprocess.Popen(
                    ffmpeg_cmd, 
                    stdin=stream_proc.stdout, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            
            buffer_info['segmenter_process'] = segmenter_proc
            
            if stream_proc.stdout:
                stream_proc.stdout.close()
            
            while not stop_flag.is_set():
                if segmenter_proc.poll() is not None:
                    break
                if stream_proc.poll() is not None:
                    break
                
                seg_files = sorted(glob.glob(os.path.join(temp_dir, "segment_*.ts")))
                if len(seg_files) > max_segments:
                    for old_seg in seg_files[:-max_segments]:
                        try:
                            os.remove(old_seg)
                        except Exception:
                            pass
                        time.sleep(1)
                
        except Exception:
            pass
        finally:
            if stream_proc and stream_proc.poll() is None:
                stream_proc.terminate()
                try:
                    stream_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    stream_proc.kill()
                    
            if segmenter_proc and segmenter_proc.poll() is None:
                segmenter_proc.terminate()
                try:
                    segmenter_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    segmenter_proc.kill()
                    
            buffer_info['is_running'] = False
            
    def stop_clipping(self, streamer_name):
        if streamer_name in self.clip_buffers:
            buffer_info = self.clip_buffers[streamer_name]
            buffer_info['stop_flag'].set()
            
            if buffer_info.get('stream_process'):
                proc = buffer_info['stream_process']
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        
            if buffer_info.get('segmenter_process'):
                proc = buffer_info['segmenter_process']
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        
            if streamer_name in self.active_clips:
                thread = self.active_clips[streamer_name]
                thread.join(timeout=10)
                del self.active_clips[streamer_name]
                
            temp_dir = buffer_info.get('temp_dir')
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
                    
            del self.clip_buffers[streamer_name]
            
    def save_clip(self, streamer_name):
        """Save clip to the hardcoded directory structure: Output/Streamername/Clips/"""
        if streamer_name not in self.clip_buffers:
            return None
            
        buffer_info = self.clip_buffers[streamer_name]
        temp_dir = buffer_info['temp_dir']
        
        # Use hardcoded directory structure for clips
        clips_path = self.config.get_streamer_clips_path(streamer_name)
        os.makedirs(clips_path, exist_ok=True)
        
        # Calculate clip timestamps
        clip_start_time = buffer_info.get('start_time', datetime.now())
        clip_end_time = datetime.now()
        
        # Format timestamps for filename
        start_timestamp = clip_start_time.strftime("%H-%M-%S")
        end_timestamp = clip_end_time.strftime("%H-%M-%S")
        
        # Use new naming format for clips
        filename = FileNamingUtils.generate_clip_name(
            streamer_name, 
            start_timestamp, 
            end_timestamp
        )
        output_file = os.path.join(clips_path, filename)
        
        seg_files = sorted(glob.glob(os.path.join(temp_dir, "segment_*.ts")))
        
        if not seg_files:
            return None
            
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, 'w') as f:
            for seg in seg_files:
                f.write(f"file '{seg}'\n")
                
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_file
        ]
        
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    text=True
                )
                
            if result.returncode == 0 and os.path.exists(output_file):
                return output_file
            else:
                return None
                
        except Exception:
            return None