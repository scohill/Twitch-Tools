#utils/file_naming.py
import os
import random
from datetime import datetime
from pathlib import Path

class FileNamingUtils:
    """Utility class for consistent file naming across the application"""
    
    @staticmethod
    def get_date_string():
        """Get formatted date string like 'June 5 2025'"""
        return datetime.now().strftime("%B %d %Y")
    
    @staticmethod
    def get_random_number():
        """Generate a random number for uniqueness"""
        return random.randint(100000, 999999)
    
    @staticmethod
    def sanitize_filename(filename):
        """Remove invalid characters from filename"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    
    @staticmethod
    def generate_live_vod_name(streamer_name, extension="mp4"):
        """Generate name for live VOD downloads
        Format: [Live] StreamerName - June 5 2025 - Randomnumber
        """
        date_str = FileNamingUtils.get_date_string()
        random_num = FileNamingUtils.get_random_number()
        filename = f"[Live] {streamer_name} - {date_str} - {random_num}.{extension}"
        return FileNamingUtils.sanitize_filename(filename)
    
    @staticmethod
    def generate_clip_name(streamer_name, start_timestamp=None, end_timestamp=None, extension="mp4"):
        """Generate name for clips
        Format: [Clip] StreamerName - June 5 2025 - start_timestamp - end_timestamp
        """
        date_str = FileNamingUtils.get_date_string()
        
        # If timestamps not provided, use current time
        if not start_timestamp:
            start_timestamp = datetime.now().strftime("%H-%M-%S")
        if not end_timestamp:
            end_timestamp = datetime.now().strftime("%H-%M-%S")
            
        filename = f"[Clip] {streamer_name} - {date_str} - {start_timestamp} - {end_timestamp}.{extension}"
        return FileNamingUtils.sanitize_filename(filename)
    
    @staticmethod
    def generate_m3u8_vod_name(streamer_name, extension="mp4"):
        """Generate name for M3U8 VOD downloads
        Format: [VOD] StreamerName - June 5 2025 - random number
        """
        date_str = FileNamingUtils.get_date_string()
        random_num = FileNamingUtils.get_random_number()
        filename = f"[VOD] {streamer_name} - {date_str} - {random_num}.{extension}"
        return FileNamingUtils.sanitize_filename(filename)
    
    @staticmethod
    def generate_frames_name(original_video_name, method, fps_or_threshold):
        """Generate name for frame extraction
        Format: [Frames] Originalvideoname - Method (scene, keyframes, frames) - fps/threshold
        """
        # Remove extension from original video name
        base_name = Path(original_video_name).stem
        
        # Format method and parameter
        if method.lower() == "fixed interval (fps)" or method.lower() == "fps" or method.lower() == "frames":
            method_str = f"frames - {fps_or_threshold}"
        elif method.lower() == "scene detection" or method.lower() == "scene":
            method_str = f"scene - {fps_or_threshold}"
        elif method.lower() == "keyframes only" or method.lower() == "keyframes":
            method_str = "keyframes"
        else:
            method_str = f"{method} - {fps_or_threshold}"
        
        folder_name = f"[Frames] {base_name} - {method_str}"
        return FileNamingUtils.sanitize_filename(folder_name)
    
    @staticmethod
    def generate_trim_name(original_video_name, start_timestamp, end_timestamp, extension="mp4"):
        """Generate name for video trims
        Format: [Trim] Originalvideoname - start_timestamp - end_timestamp
        """
        # Remove extension from original video name
        base_name = Path(original_video_name).stem
        
        # Format timestamps (remove colons for filename compatibility)
        start_str = start_timestamp.replace(":", "-")
        end_str = end_timestamp.replace(":", "-")
        
        filename = f"[Trim] {base_name} - {start_str} - {end_str}.{extension}"
        return FileNamingUtils.sanitize_filename(filename)
    
    @staticmethod
    def format_timestamp_for_filename(timestamp_seconds):
        """Convert seconds to HH-MM-SS format for filenames"""
        hours = int(timestamp_seconds // 3600)
        minutes = int((timestamp_seconds % 3600) // 60)
        seconds = int(timestamp_seconds % 60)
        return f"{hours:02d}-{minutes:02d}-{seconds:02d}"