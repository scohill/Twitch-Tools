#utils/config.py
import json
import os
from pathlib import Path

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.twitch_monitor'
        self.config_file = self.config_dir / 'config.json'
        self.config_dir.mkdir(exist_ok=True)
        
        self.base_recordings_dir = Path.cwd() / 'Output'
        self.data = self.load()
        
    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    
                if 'streamers' in data:
                    for streamer_name, settings in data['streamers'].items():
                        if 'auto_download' in settings:
                            if isinstance(settings['auto_download'], str):
                                settings['auto_download'] = settings['auto_download'].lower() == 'true'
                        if 'auto_clip' in settings:
                            if isinstance(settings['auto_clip'], str):
                                settings['auto_clip'] = settings['auto_clip'].lower() == 'true'
                                
                        # Remove old path settings - we'll use hardcoded structure
                        if 'download_path' in settings:
                            del settings['download_path']
                        if 'clips_path' in settings:
                            del settings['clips_path']
                                
                return data
            except Exception:
                pass
                
        return {
            'streamers': {},
            'default_quality': 'best',
            'default_format': 'mp4',
            'base_recordings_path': str(self.base_recordings_dir),
            'default_m3u8_path': str(self.base_recordings_dir / 'VOD Downloads'),
            'default_frames_path': str(self.base_recordings_dir / 'Frames'),
            'default_trims_path': str(self.base_recordings_dir / 'Trims')
        }
        
    def save(self):
        try:
            save_data = json.loads(json.dumps(self.data))
            
            if 'streamers' in save_data:
                for streamer_name, settings in save_data['streamers'].items():
                    if 'auto_download' in settings:
                        settings['auto_download'] = bool(settings['auto_download'])
                    if 'auto_clip' in settings:
                        settings['auto_clip'] = bool(settings['auto_clip'])
                    
                    # Remove path settings from save data - we don't store paths anymore
                    if 'download_path' in settings:
                        del settings['download_path']
                    if 'clips_path' in settings:
                        del settings['clips_path']
            
            with open(self.config_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception:
            pass
            
    def get_streamers(self):
        return list(self.data.get('streamers', {}).keys())
        
    def add_streamer(self, streamer_name):
        if 'streamers' not in self.data:
            self.data['streamers'] = {}
            
        if streamer_name not in self.data['streamers']:
            # Only store basic settings - no paths
            self.data['streamers'][streamer_name] = {
                'auto_download': False,
                'auto_clip': False,
                'quality': self.data.get('default_quality', 'best'),
                'format': self.data.get('default_format', 'mp4')
            }
            self.save()
            
    def remove_streamer(self, streamer_name):
        if 'streamers' in self.data and streamer_name in self.data['streamers']:
            del self.data['streamers'][streamer_name]
            self.save()
            
    def get_streamer_settings(self, streamer_name):
        settings = self.data.get('streamers', {}).get(streamer_name, {})
        
        if 'auto_download' in settings:
            settings['auto_download'] = bool(settings['auto_download'])
        if 'auto_clip' in settings:
            settings['auto_clip'] = bool(settings['auto_clip'])
            
        return settings
        
    def update_streamer_setting(self, streamer_name, key, value):
        if 'streamers' in self.data and streamer_name in self.data['streamers']:
            # Don't allow path settings to be updated
            if key in ['download_path', 'clips_path']:
                return
                
            if key in ['auto_download', 'auto_clip']:
                value = bool(value)
                
            self.data['streamers'][streamer_name][key] = value
            self.save()
    
    def get_streamer_vod_path(self, streamer_name):
        """Get the hardcoded VODs path for a streamer"""
        base_path = self.data.get('base_recordings_path', str(self.base_recordings_dir))
        return os.path.join(base_path, streamer_name, "VODs")
    
    def get_streamer_clips_path(self, streamer_name):
        """Get the hardcoded Clips path for a streamer"""
        base_path = self.data.get('base_recordings_path', str(self.base_recordings_dir))
        return os.path.join(base_path, streamer_name, "Clips")
            
    def get_default_download_path(self):
        base_path = self.data.get('base_recordings_path', str(self.base_recordings_dir))
        return base_path
        
    def get_default_clips_path(self):
        base_path = self.data.get('base_recordings_path', str(self.base_recordings_dir))
        return base_path
        
    def get_m3u8_download_path(self):
        return self.data.get('default_m3u8_path', str(self.base_recordings_dir / 'VOD Downloads'))
        
    def get_frames_base_path(self):
        return self.data.get('default_frames_path', str(self.base_recordings_dir / 'Frames'))
        
    def get_trims_base_path(self):
        """Get the base path for video trims"""
        return self.data.get('default_trims_path', str(self.base_recordings_dir / 'Trims'))
        
    def update_default_setting(self, key, value):
        # Don't allow updating path settings for streamers
        if key not in ['download_path', 'clips_path']:
            self.data[key] = value
            self.save()