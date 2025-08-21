from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLineEdit, QLabel, QTextEdit, QFileDialog,
                               QGroupBox, QComboBox, QProgressBar,
                               QMessageBox, QApplication, QTabWidget, QScrollArea, QSpinBox, QInputDialog)
from PySide6.QtCore import Qt, QThread, Signal, QMutex, QWaitCondition
import subprocess
import os
import re
import shutil
import requests
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import uuid
import hashlib
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from utils.file_naming import FileNamingUtils
import gc
import stat

class StyleManager:
    """Centralized style management for consistent UI"""
    
    @staticmethod
    def button_style(bg_color="#4a4a4a", hover_color="#5a5a5a"):
        return f"""
        QPushButton {{
            padding: 12px 24px;
            background-color: {bg_color};
            border: none;
            border-radius: 6px;
            color: #ffffff;
            font-weight: bold;
            font-size: 14px;
            min-height: 20px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:disabled {{
            background-color: #2a2a2a;
            color: #666666;
        }}
        """
    
    @staticmethod
    def input_style():
        return """
        QLineEdit {
            padding: 12px;
            font-size: 14px;
            border: 2px solid #4a4a4a;
            border-radius: 6px;
            background-color: #1e1e1e;
            color: #ffffff;
            selection-background-color: #9147ff;
            selection-color: #ffffff;
            min-height: 24px;
        }
        QLineEdit:focus {
            border-color: #9147ff;
            background-color: #2a2a2a;
        }
        QLineEdit:disabled {
            background-color: #0a0a0a;
            color: #666666;
        }
        QLineEdit::placeholder {
            color: #888888;
        }
        """
    
    @staticmethod
    def group_style():
        return """
        QGroupBox {
            font-weight: bold;
            font-size: 14px;
            border: 2px solid #4a4a4a;
            border-radius: 8px;
            margin-top: 15px;
            padding-top: 15px;
            padding-bottom: 10px;
            padding-left: 10px;
            padding-right: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 10px;
            color: #ffffff;
        }
        """
    
    @staticmethod
    def console_style():
        return """
        QTextEdit {
            background-color: #1e1e1e;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            color: #00ff00;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            padding: 12px;
            line-height: 1.4;
        }
        """
    
    @staticmethod
    def progress_style():
        return """
        QProgressBar {
            border: 2px solid #4a4a4a;
            border-radius: 6px;
            text-align: center;
            background-color: #2b2b2b;
            color: #ffffff;
            height: 30px;
            font-size: 12px;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: #9147ff;
            border-radius: 4px;
        }
        """
    
    @staticmethod
    def label_style():
        return """
        QLabel {
            color: #ffffff;
            font-size: 13px;
            padding: 2px;
        }
        """

class TimeUtils:
    """Utility class for time-related operations"""
    
    @staticmethod
    def parse_time_string(time_str):
        """Convert HH:MM:SS or MM:SS or SS to seconds"""
        if not time_str:
            return 0
        
        try:
            parts = time_str.strip().split(':')
            if len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:  # SS
                return int(parts[0])
        except:
            pass
        
        return 0
    
    @staticmethod
    def format_seconds(seconds):
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

class DateParser:
    """Centralized date parsing functionality"""
    
    MONTH_MAP = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9,
        'oct': 10, 'nov': 11, 'dec': 12
    }
    
    @classmethod
    def parse_various_formats(cls, date_str):
        """Try to parse various date formats"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Remove common prefixes
        prefixes = [
            "Started at", "Stream started", "Started on", "Start time:",
            "Date:", "Time:", "Stream date:", "Streamed on", "Stream starting"
        ]
        
        for prefix in prefixes:
            if date_str.lower().startswith(prefix.lower()):
                date_str = date_str[len(prefix):].strip()
        
        # Try standard formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%d/%m/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%B %d, %Y %H:%M:%S",
            "%b %d, %Y %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        
        # Try regex patterns
        return cls._try_regex_patterns(date_str)
    
    @classmethod
    def _try_regex_patterns(cls, date_str):
        """Try various regex patterns to extract date"""
        patterns = [
            # ISO format
            (r'(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2}:\d{2})',
             lambda m: f"{m.group(1)} {m.group(2)}"),
            
            # DD/MM/YYYY format
            (r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2}:\d{2}:\d{2})',
             lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)} {m.group(4)}"),
            
            # Month name formats
            (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})\s+(\d{2}:\d{2})',
             lambda m: cls._convert_month_format(m)),
        ]
        
        for pattern, formatter in patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    result = formatter(match)
                    if result and re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', result):
                        if not result.endswith(':00'):
                            result += ":00"
                        return result
                except:
                    continue
        
        return None
    
    @classmethod
    def _convert_month_format(cls, match):
        """Convert month name to number"""
        month_name = match.group(1).lower()
        month_num = cls.MONTH_MAP.get(month_name, 1)
        day = match.group(2).zfill(2)
        year = match.group(3)
        time = match.group(4)
        return f"{year}-{month_num:02d}-{day} {time}:00"

class VODFinderThread(QThread):
    """Thread for finding VOD M3U8 URLs"""
    
    progress_update = Signal(str)
    found_url = Signal(str)
    error = Signal(str)
    
    def __init__(self, streamer_name, video_id, timestamp, domains):
        super().__init__()
        self.streamer_name = streamer_name
        self.video_id = video_id
        self.timestamp = timestamp
        self.domains = domains
        self._should_stop = False
    
    def stop(self):
        self._should_stop = True
    
    async def check_m3u8_url(self, session, url, retries=3, timeout=30):
        """Check if an M3U8 URL is valid"""
        for attempt in range(retries):
            if self._should_stop:
                return None
            
            try:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.text()
                        if data and "#EXTM3U" in data:
                            return url
            except:
                if attempt == retries - 1:
                    return None
                continue
        
        return None
    
    async def find_vod_m3u8_async(self):
        """Find M3U8 URL for a Twitch VOD with timestamp offset testing"""
        m3u8_urls = []
        base_time = datetime.strptime(self.timestamp, "%Y-%m-%d %H:%M:%S")
        
        for minute_offset in range(-1, 2):
            if self._should_stop:
                return None
            
            # Add minute offset
            test_time = base_time + timedelta(minutes=minute_offset)
            
            # Generate URLs for each second within this minute
            for seconds in range(60):
                if self._should_stop:
                    return None
                
                epoch_timestamp = int((test_time + timedelta(seconds=seconds) -
                                     datetime(1970, 1, 1)).total_seconds())
                
                # Generate SHA1 hash
                hash_input = f"{self.streamer_name}_{self.video_id}_{epoch_timestamp}"
                url_hash = hashlib.sha1(hash_input.encode('utf-8')).hexdigest()[:20]
                
                # Create M3U8 URLs for each domain
                for domain in self.domains:
                    m3u8_url = f"{domain}{url_hash}_{self.streamer_name}_{self.video_id}_{epoch_timestamp}/chunked/index-dvr.m3u8"
                    m3u8_urls.append(m3u8_url)
        
        self.progress_update.emit(f"Generated {len(m3u8_urls)} possible URLs to check...")
        self.progress_update.emit(f"Testing timestamps from {(base_time - timedelta(minutes=5)).strftime('%H:%M:%S')} to {(base_time + timedelta(minutes=5)).strftime('%H:%M:%S')}")
        
        # Check URLs asynchronously
        try:
            async with aiohttp.ClientSession() as session:
                tasks = [self.check_m3u8_url(session, url) for url in m3u8_urls]
                
                for index, task in enumerate(asyncio.as_completed(tasks), 1):
                    if self._should_stop:
                        return None
                    
                    try:
                        url = await task
                        self.progress_update.emit(f"Checking {index}/{len(m3u8_urls)} URLs...")
                        if url:
                            return url
                    except:
                        continue
        
        except Exception as e:
            self.error.emit(f"Error during URL search: {str(e)}")
            return None
        
        return None
    
    def run(self):
        """Run the VOD finder"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            m3u8_url = loop.run_until_complete(self.find_vod_m3u8_async())
            
            if m3u8_url and not self._should_stop:
                self.found_url.emit(m3u8_url)
            elif not self._should_stop:
                self.error.emit("No valid M3U8 URL found")
        
        except Exception as e:
            if not self._should_stop:
                self.error.emit(f"Error: {str(e)}")
        finally:
            loop.close()

class StreamInfoExtractor:
    """Extract stream information from tracking websites"""
    
    @staticmethod
    def get_driver():
        """Create and configure Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Add more options for stability
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Disable images and CSS for faster loading
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Use webdriver-manager to automatically download and manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    @staticmethod
    def extract_with_fallback(url):
        """Try Selenium first, then fall back to manual instructions if it fails"""
        try:
            # Try with Selenium
            result = StreamInfoExtractor.extract_from_url(url)
            if result[0] or result[1]:  # If we got at least some info
                return result
        except Exception:
            pass
        
        # Extract what we can from URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        streamer = None
        vod_id = None
        
        # Try to extract from URL patterns
        if 'streamscharts.com' in domain:
            match = re.search(r'/channels/([^/]+)/streams/(\d+)', url)
            if match:
                streamer = match.group(1).lower()
                vod_id = match.group(2)
        
        # If we couldn't extract VOD ID, try generic patterns
        if not vod_id:
            vod_id = StreamInfoExtractor.extract_vod_id_from_url(url)
        
        instructions = StreamInfoExtractor.get_manual_instructions(domain)
        return streamer, vod_id, None, f"Automatic extraction failed. {instructions}"
    
    @staticmethod
    def extract_vod_id_from_url(url):
        """Try to extract just the VOD ID from various URL formats"""
        patterns = [
            r'/streams/(\d{10,})',
            r'/stream/(\d{10,})',
            r'/(\d{10,})/?$',
            r'[?&]v=(\d{10,})',
            r'/videos/(\d{10,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def get_manual_instructions(domain):
        """Get manual extraction instructions for a domain"""
        if 'streamscharts.com' in domain:
            return (
                "\n\nManual extraction needed:\n"
                "1. Open the Streamscharts page in your browser\n"
                "2. Look for the time element (e.g., '25 May 2025, 18:55')\n"
                "3. The time should be in UTC\n"
                "4. Enter as: YYYY-MM-DD HH:MM:SS"
            )
        else:
            return (
                "\n\nManual extraction needed:\n"
                "1. Find the stream start time on the page\n"
                "2. Convert to UTC timezone\n"
                "3. Enter timestamp as: YYYY-MM-DD HH:MM:SS"
            )
    
    @staticmethod
    def extract_from_url(url):
        """Extract streamer name, VOD ID, and timestamp from tracking site URLs"""
        driver = None
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Create driver
            driver = StreamInfoExtractor.get_driver()
            
            if 'streamscharts.com' in domain:
                return StreamInfoExtractor._extract_from_streamscharts(url, driver)
            else:
                return None, None, None, "Unsupported website. Supported site: Streamscharts"
        
        except Exception as e:
            return None, None, None, f"Error extracting info: {str(e)}"
        finally:
            if driver:
                driver.quit()
    
    @staticmethod
    def _extract_from_streamscharts(url, driver):
        """Extract info from Streamscharts URL using Selenium"""
        try:
            # Extract from URL first
            match = re.search(r'/channels/([^/]+)/streams/(\d+)', url)
            if not match:
                return None, None, None, "Invalid Streamscharts URL format"
            
            streamer_name = match.group(1).lower()
            vod_id = match.group(2)
            
            # Load the page
            driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 15)
            
            # Give the page time to fully render
            time.sleep(2)
            
            timestamp = None
            found_texts = []
            
            # Streamscharts specific selectors
            timestamp_selectors = [
                (By.TAG_NAME, "time"),
                (By.XPATH, "//time[@datetime]"),
                (By.CSS_SELECTOR, "time.ml-2.font-bold"),
                (By.CSS_SELECTOR, "time[data-tippy-content]"),
                (By.XPATH, "//time[contains(@class, 'font-bold')]"),
            ]
            
            for by, selector in timestamp_selectors:
                try:
                    elements = driver.find_elements(by, selector)
                    for element in elements:
                        # Get datetime attribute
                        datetime_attr = element.get_attribute('datetime')
                        if datetime_attr:
                            found_texts.append(f"datetime: {datetime_attr}")
                            # Parse the streamscharts format
                            parsed = StreamInfoExtractor._parse_streamscharts_date(datetime_attr)
                            if parsed:
                                timestamp = parsed
                                break
                        
                        # Try text content
                        text = element.text.strip()
                        if text:
                            found_texts.append(f"text: {text}")
                            parsed = DateParser.parse_various_formats(text)
                            if parsed:
                                timestamp = parsed
                                break
                except:
                    continue
                
                if timestamp:
                    break
            
            if timestamp:
                return streamer_name, vod_id, timestamp, None
            else:
                debug_info = f"Found texts: {found_texts[:3]}" if found_texts else "No timestamp texts found"
                return streamer_name, vod_id, None, f"Could not find timestamp. {debug_info}. Please enter manually."
        
        except Exception as e:
            return None, None, None, f"Error parsing Streamscharts: {str(e)}"
    
    @staticmethod
    def _parse_streamscharts_date(date_str):
        """Parse Streamscharts date format"""
        try:
            # Clean the string
            date_str = date_str.strip()
            
            # Pattern 1: DD-MM-YYYY HH:MM format
            if re.match(r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}', date_str):
                dt = datetime.strptime(date_str, "%d-%m-%Y %H:%M")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Pattern 2: DD-MM-YYYY HH:MM:SS format
            if re.match(r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}', date_str):
                dt = datetime.strptime(date_str, "%d-%m-%Y %H:%M:%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Pattern 3: "25 May 2025, 18:55" format
            pattern = r'(\d{1,2})\s+(\w+)\s+(\d{4}),?\s+(\d{2}):(\d{2})'
            match = re.search(pattern, date_str)
            if match:
                day = int(match.group(1))
                month_name = match.group(2)
                year = int(match.group(3))
                hour = int(match.group(4))
                minute = int(match.group(5))
                
                month = DateParser.MONTH_MAP.get(month_name.lower())
                if month:
                    dt = datetime(year, month, day, hour, minute, 0)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
        
        except Exception:
            pass
        
        # Fall back to general parsing
        return DateParser.parse_various_formats(date_str)

class FastM3U8DownloadThread(QThread):
    """Fast M3U8 downloader with parallel segment downloading and pause/resume functionality"""
    
    progress_update = Signal(str)
    progress_value = Signal(int)
    download_finished = Signal(bool, str)
    speed_update = Signal(str)
    
    def __init__(self, url, output_path, start_time=None, duration=None, max_workers=8, chunk_size=1024*1024):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.start_time = start_time
        self.duration = duration
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self._should_stop = False
        self._should_abort = False
        self._is_paused = False
        self.temp_dir = None
        self.partial_output_path = None
        self.downloaded_segments = 0
        self.total_segments = 0
        self.download_queue = queue.Queue()
        self.completed_segments = {}
        self.failed_segments = set()
        self.download_lock = threading.Lock()
        self.start_time_download = None
        self.total_bytes_downloaded = 0
        
        # Pause/resume synchronization
        self.pause_mutex = QMutex()
        self.pause_condition = QWaitCondition()
    
    def stop(self):
        """Stop download but save what's been downloaded"""
        self._should_stop = True
        self._force_stop_workers()
        self.resume()  # Wake up if paused
    
    def abort(self):
        """Abort download and delete partial files"""
        self._should_abort = True
        self._should_stop = True
        self._force_stop_workers()
        self.resume()  # Wake up if paused
    
    def _force_stop_workers(self):
        """Force stop all worker threads immediately"""
        # Signal all workers to stop
        self.progress_update.emit("🛑 Forcing all workers to stop...")
        
        # Clear the download queue to prevent new tasks
        try:
            while not self.download_queue.empty():
                self.download_queue.get_nowait()
        except:
            pass
    
    def pause(self):
        """Pause the download"""
        self.pause_mutex.lock()
        self._is_paused = True
        self.pause_mutex.unlock()
        self.progress_update.emit("⏸️ Download paused")
    
    def resume(self):
        """Resume the download"""
        self.pause_mutex.lock()
        self._is_paused = False
        self.pause_condition.wakeAll()
        self.pause_mutex.unlock()
        if not self._should_stop and not self._should_abort:
            self.progress_update.emit("▶️ Download resumed")
    
    def is_paused(self):
        """Check if download is paused"""
        return self._is_paused
    
    def _check_pause(self):
        """Check if paused and wait if necessary"""
        self.pause_mutex.lock()
        while self._is_paused and not self._should_stop and not self._should_abort:
            self.pause_condition.wait(self.pause_mutex)
        self.pause_mutex.unlock()
    
    def transform_url(self, url):
        """Transform unmuted.ts URLs to muted.ts"""
        if url.endswith('-unmuted.ts'):
            transformed_url = url.replace('-unmuted.ts', '-muted.ts')
            if not hasattr(self, '_transform_count'):
                self._transform_count = 0
            self._transform_count += 1
            if self._transform_count <= 3:
                self.progress_update.emit(f"🔄 Transformed: {url.split('/')[-1]} → {transformed_url.split('/')[-1]}")
            elif self._transform_count == 4:
                self.progress_update.emit("🔄 (Further URL transformations will be silent)")
            return transformed_url
        return url
    
    def parse_m3u8(self, m3u8_url):
        """Parse M3U8 file and extract segment URLs and durations"""
        try:
            if m3u8_url.startswith("http"):
                response = requests.get(m3u8_url, timeout=10)
                response.raise_for_status()
                lines = response.text.splitlines()
                base_url = m3u8_url.rsplit('/', 1)[0] + '/'
            else:
                with open(m3u8_url, "r") as f:
                    lines = f.read().splitlines()
                base_url = "file://" + os.path.dirname(os.path.abspath(m3u8_url)) + "/"
            
            segment_urls = []
            segment_durations = []
            duration = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    try:
                        duration = float(line.split(":")[1].split(",")[0])
                    except:
                        duration = None
                elif line and not line.startswith("#"):
                    if line.startswith("http"):
                        segment_url = line
                    else:
                        segment_url = urljoin(base_url, line)
                    
                    segment_url = self.transform_url(segment_url)
                    segment_urls.append(segment_url)
                    segment_durations.append(duration if duration is not None else 0)
                    duration = None
            
            return segment_urls, segment_durations
        
        except Exception as e:
            self.progress_update.emit(f"❌ Error parsing M3U8: {str(e)}")
            return []

    def trim_segments(self, segment_urls, segment_durations, start_sec, end_sec):
        """Get segments for a specific time range"""
        current_time = 0
        start_idx = 0
        end_idx = len(segment_urls)
        
        for i, dur in enumerate(segment_durations):
            if current_time + dur > start_sec:
                start_idx = i
                break
            current_time += dur
        
        current_time = 0
        for i, dur in enumerate(segment_durations):
            if current_time >= end_sec:
                end_idx = i
                break
            current_time += dur
        
        return segment_urls[start_idx:end_idx], segment_durations[start_idx:end_idx]
    
    def download_segment(self, url, segment_index, temp_dir):
        """Download a single segment"""
        segment_path = None
        file_handle = None
        
        try:
            self._check_pause()
            
            if self._should_stop or self._should_abort:
                return False
            
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            segment_path = os.path.join(temp_dir, f"segment_{segment_index:06d}.ts")
            
            file_handle = open(segment_path, 'wb')
            
            for chunk in response.iter_content(chunk_size=self.chunk_size):
                if self._should_stop or self._should_abort:
                    # Close file handle immediately on stop/abort
                    if file_handle:
                        file_handle.close()
                        file_handle = None
                    return False
                
                self._check_pause()
                
                if chunk:
                    file_handle.write(chunk)
                    with self.download_lock:
                        self.total_bytes_downloaded += len(chunk)
            
            # Close file handle before updating completed segments
            if file_handle:
                file_handle.close()
                file_handle = None
            
            with self.download_lock:
                self.completed_segments[segment_index] = segment_path
                self.downloaded_segments += 1
                progress = int((self.downloaded_segments / self.total_segments) * 100)
                self.progress_value.emit(progress)
                
                if self.start_time_download:
                    elapsed = time.time() - self.start_time_download
                    if elapsed > 0:
                        speed_mbps = (self.total_bytes_downloaded / (1024 * 1024)) / elapsed
                        self.speed_update.emit(f"{speed_mbps:.2f} MB/s")
            
            return True
        
        except Exception as e:
            # Ensure file handle is closed on error
            if file_handle:
                try:
                    file_handle.close()
                except:
                    pass
            
            with self.download_lock:
                self.failed_segments.add(segment_index)
            
            self.progress_update.emit(f"❌ Failed to download segment {segment_index}: {str(e)}")
            return False
    
    def run(self):
        """Main download thread execution"""
        try:
            self.start_time_download = time.time()
            self.progress_update.emit("📋 Parsing M3U8 file...")
            
            segment_urls, segment_durations = self.parse_m3u8(self.url)
            if not segment_urls:
                self.download_finished.emit(False, "No segments found in M3U8 file")
                return
            
            if self.start_time is not None:
                end_time = self.start_time + (self.duration if self.duration else sum(segment_durations))
                segment_urls, segment_durations = self.trim_segments(
                    segment_urls, segment_durations, self.start_time, end_time
                )
                self.progress_update.emit(f"⏱️ Trimmed to {len(segment_urls)} segments")
            
            self.total_segments = len(segment_urls)
            if self.total_segments == 0:
                self.download_finished.emit(False, "No segments in specified time range")
                return
            
            self.progress_update.emit(f"📊 Found {self.total_segments} segments to download")
            
            # Create temporary directory
            self.temp_dir = os.path.join(os.path.dirname(self.output_path), f"temp_{uuid.uuid4().hex[:8]}")
            os.makedirs(self.temp_dir, exist_ok=True)
            self.progress_update.emit(f"📁 Created temp directory: {self.temp_dir}")
            
            self.progress_update.emit(f"⚡ Starting parallel download with {self.max_workers} workers...")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_index = {
                    executor.submit(self.download_segment, url, i, self.temp_dir): i
                    for i, url in enumerate(segment_urls)
                }
                
                for future in as_completed(future_to_index):
                    if self._should_stop or self._should_abort:
                        # Cancel all remaining futures immediately
                        self.progress_update.emit("🛑 Cancelling remaining downloads...")
                        for f in future_to_index:
                            if not f.done():
                                f.cancel()
                        # Force shutdown of executor
                        executor.shutdown(wait=False)
                        break
                    
                    segment_index = future_to_index[future]
                    try:
                        success = future.result(timeout=1)  # Add timeout to prevent hanging
                        if not success and segment_index not in self.failed_segments:
                            self.failed_segments.add(segment_index)
                    except Exception as e:
                        self.failed_segments.add(segment_index)
                        self.progress_update.emit(f"❌ Error downloading segment {segment_index}: {str(e)}")
            
            if self._should_abort:
                self.progress_update.emit("⏹️ Download aborted by user")
                self._cleanup_temp_files()
                self.download_finished.emit(False, "Download aborted by user")
                return
            
            # Retry failed segments
            if self.failed_segments and not self._should_stop:
                self.progress_update.emit(f"🔄 Retrying {len(self.failed_segments)} failed segments...")
                retry_count = 0
                max_retries = 3
                
                while self.failed_segments and retry_count < max_retries and not self._should_stop and not self._should_abort:
                    retry_count += 1
                    failed_copy = self.failed_segments.copy()
                    self.failed_segments.clear()
                    
                    with ThreadPoolExecutor(max_workers=min(self.max_workers, len(failed_copy))) as executor:
                        retry_futures = {
                            executor.submit(self.download_segment, segment_urls[i], i, self.temp_dir): i
                            for i in failed_copy
                        }
                        
                        for future in as_completed(retry_futures):
                            if self._should_stop or self._should_abort:
                                # Cancel all remaining retry futures
                                for f in retry_futures:
                                    if not f.done():
                                        f.cancel()
                                executor.shutdown(wait=False)
                                break
                            
                            segment_index = retry_futures[future]
                            try:
                                success = future.result(timeout=1)
                                if not success:
                                    self.failed_segments.add(segment_index)
                            except Exception:
                                self.failed_segments.add(segment_index)
            
            # Concatenate segments
            if not self._should_stop and not self._should_abort:
                self.progress_update.emit("🔗 Concatenating segments...")
                success = self._concatenate_segments()
                
                if success:
                    file_size = os.path.getsize(self.output_path) if os.path.exists(self.output_path) else 0
                    size_mb = file_size / (1024 * 1024)
                    
                    if self.failed_segments:
                        message = f"Download completed with {len(self.failed_segments)} failed segments. File size: {size_mb:.1f} MB"
                    else:
                        message = f"Download completed successfully! File size: {size_mb:.1f} MB"
                    
                    self._cleanup_temp_files()
                    self.download_finished.emit(True, message)
                else:
                    self._cleanup_temp_files()
                    self.download_finished.emit(False, "Failed to concatenate segments")
            else:
                self.progress_update.emit("⏹️ Creating partial file from downloaded segments...")
                self._concatenate_segments()
                
                file_size = os.path.getsize(self.output_path) if os.path.exists(self.output_path) else 0
                size_mb = file_size / (1024 * 1024)
                message = f"Partial download saved. Downloaded {self.downloaded_segments}/{self.total_segments} segments. File size: {size_mb:.1f} MB"
                self._cleanup_temp_files()
                self.download_finished.emit(True, message)
        
        except Exception as e:
            self._cleanup_temp_files()
            self.download_finished.emit(False, f"Download error: {str(e)}")
        finally:
            # Ensure cleanup happens even if there's an exception
            self._cleanup_temp_files()
    
    def _concatenate_segments(self):
        """Concatenate downloaded segments into final video file"""
        try:
            segment_files = []
            for i in range(self.total_segments):
                if i in self.completed_segments:
                    segment_files.append(self.completed_segments[i])
            
            if not segment_files:
                return False
            
            concat_file = os.path.join(self.temp_dir, "concat_list.txt")
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment_file in segment_files:
                    abs_path = os.path.abspath(segment_file)
                    ffmpeg_path = abs_path.replace('\\', '/').replace("'", "\\'")
                    f.write(f"file '{ffmpeg_path}'\n")
            
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', concat_file, '-c', 'copy', self.output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                self.progress_update.emit(f"❌ FFmpeg error: {result.stderr}")
                return False
        
        except Exception as e:
            self.progress_update.emit(f"❌ Concatenation error: {str(e)}")
            return False
    
    def _cleanup_temp_files(self):
        """Clean up temporary files and directories"""
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return
        
        try:
            self.progress_update.emit("🧹 Cleaning up temporary files...")
            
            # Remove all files in temp directory
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        # Make file writable before deletion (Windows compatibility)
                        os.chmod(file_path, stat.S_IWRITE)
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    self.progress_update.emit(f"⚠️ Could not delete {filename}: {str(e)}")
            
            # Remove temp directory
            try:
                os.rmdir(self.temp_dir)
                self.progress_update.emit("✅ Temporary files cleaned up")
            except Exception as e:
                self.progress_update.emit(f"⚠️ Could not remove temp directory: {str(e)}")
        
        except Exception as e:
            self.progress_update.emit(f"⚠️ Error during cleanup: {str(e)}")

class StreamInfoExtractionThread(QThread):
    """Thread for extracting stream information from tracking websites"""
    
    progress_update = Signal(str)
    extraction_finished = Signal(str, str, str, str)  # streamer, vod_id, timestamp, error
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self._should_stop = False
    
    def stop(self):
        self._should_stop = True
    
    def run(self):
        """Run the stream info extraction"""
        try:
            self.progress_update.emit("🔍 Extracting stream information...")
            
            if self._should_stop:
                return
            
            streamer, vod_id, timestamp, error = StreamInfoExtractor.extract_with_fallback(self.url)
            
            if not self._should_stop:
                self.extraction_finished.emit(streamer or "", vod_id or "", timestamp or "", error or "")
        
        except Exception as e:
            if not self._should_stop:
                self.extraction_finished.emit("", "", "", f"Error extracting info: {str(e)}")

class M3U8Downloader(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.vod_finder_thread = None
        self.download_thread = None
        self.extraction_thread = None
        self.detected_streamer = None
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        # Create main layout for the widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
            QScrollBar:vertical {
                background-color: #3a3a3a;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #9147ff;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #7c3aed;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #3a3a3a;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #9147ff;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #7c3aed;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
        """)
        
        # Create content widget that will hold all the sections
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(25, 25, 25, 25)
        
        # VOD Finder Section
        finder_group = QGroupBox("🔍 VOD Finder")
        finder_group.setStyleSheet(StyleManager.group_style())
        finder_group.setFixedHeight(130)
        finder_layout = QVBoxLayout(finder_group)
        finder_layout.setSpacing(10)
        
        # Instructions
        instructions = QLabel(
            "📋 Paste a URL from Streamscharts to automatically find the VOD info then Click on Find VOD"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #cccccc; margin-bottom: 5px; font-size: 12px; line-height: 1.3;")
        finder_layout.addWidget(instructions)
        
        # URL input
        url_layout = QHBoxLayout()
        url_layout.setSpacing(10)
        
        self.tracking_url_input = QLineEdit()
        self.tracking_url_input.setPlaceholderText("Paste tracking website URL here (e.g., https://streamscharts.com/channels/...)")
        self.tracking_url_input.setStyleSheet(StyleManager.input_style())
        
        self.find_button = QPushButton("🔍 Extract Info")
        self.find_button.clicked.connect(self.find_vod_m3u8)
        self.find_button.setStyleSheet(StyleManager.button_style("#9147ff", "#7c3aed"))
        self.find_button.setMinimumWidth(120)
        
        url_layout.addWidget(self.tracking_url_input, 1)
        url_layout.addWidget(self.find_button)
        finder_layout.addLayout(url_layout)
        
        # Manual input section
        manual_group = QGroupBox("📝 Manual Input")
        manual_group.setStyleSheet(StyleManager.group_style())
        manual_group.setFixedHeight(290)
        manual_layout = QVBoxLayout(manual_group)
        manual_layout.setSpacing(8)
        
        # Streamer name input
        streamer_layout = QHBoxLayout()
        streamer_layout.setSpacing(10)
        streamer_label = QLabel("Streamer:")
        streamer_label.setStyleSheet(StyleManager.label_style())
        streamer_label.setMinimumWidth(80)
        streamer_layout.addWidget(streamer_label)
        
        self.streamer_input = QLineEdit()
        self.streamer_input.setPlaceholderText("Enter streamer name")
        self.streamer_input.setStyleSheet(StyleManager.input_style())
        streamer_layout.addWidget(self.streamer_input, 1)
        manual_layout.addLayout(streamer_layout)
        
        # VOD ID input
        vod_layout = QHBoxLayout()
        vod_layout.setSpacing(10)
        vod_label = QLabel("VOD ID:")
        vod_label.setStyleSheet(StyleManager.label_style())
        vod_label.setMinimumWidth(80)
        vod_layout.addWidget(vod_label)
        
        self.vod_id_input = QLineEdit()
        self.vod_id_input.setPlaceholderText("Enter VOD ID (10+ digits)")
        self.vod_id_input.setStyleSheet(StyleManager.input_style())
        vod_layout.addWidget(self.vod_id_input, 1)
        manual_layout.addLayout(vod_layout)
        
        # Timestamp input
        timestamp_layout = QHBoxLayout()
        timestamp_layout.setSpacing(10)
        timestamp_label = QLabel("Timestamp:")
        timestamp_label.setStyleSheet(StyleManager.label_style())
        timestamp_label.setMinimumWidth(80)
        timestamp_layout.addWidget(timestamp_label)
        
        self.timestamp_input = QLineEdit()
        self.timestamp_input.setPlaceholderText("YYYY-MM-DD HH:MM:SS (UTC)")
        self.timestamp_input.setStyleSheet(StyleManager.input_style())
        timestamp_layout.addWidget(self.timestamp_input, 1)
        manual_layout.addLayout(timestamp_layout)
        
        # Manual find button
        self.manual_find_button = QPushButton("🔍 Find VOD")
        self.manual_find_button.clicked.connect(self.find_vod_m3u8_manual)
        self.manual_find_button.setStyleSheet(StyleManager.button_style("#9147ff", "#7c3aed"))
        manual_layout.addWidget(self.manual_find_button)
        
        # Download Section
        download_group = QGroupBox("📥 Download Settings")
        download_group.setStyleSheet(StyleManager.group_style())
        download_group.setFixedHeight(320)
        download_layout = QVBoxLayout(download_group)
        download_layout.setSpacing(10)
        
        # M3U8 URL input
        url_input_layout = QHBoxLayout()
        url_input_layout.setSpacing(10)
        url_label = QLabel("VOD M3U8 URL:")
        url_label.setStyleSheet(StyleManager.label_style())
        url_label.setMinimumWidth(80)
        url_input_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("VOD M3U8 URL will appear here or paste manually")
        self.url_input.setStyleSheet(StyleManager.input_style())
        url_input_layout.addWidget(self.url_input, 1)
        download_layout.addLayout(url_input_layout)
        
        # Time range inputs
        time_layout = QHBoxLayout()
        time_layout.setSpacing(15)
        
        start_label = QLabel("Start Time:")
        start_label.setStyleSheet(StyleManager.label_style())
        start_label.setMinimumWidth(80)
        time_layout.addWidget(start_label)
        
        self.start_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText("HH:MM:SS (optional)")
        self.start_time_input.setStyleSheet(StyleManager.input_style())
        time_layout.addWidget(self.start_time_input, 1)
        
        end_label = QLabel("End Time:")
        end_label.setStyleSheet(StyleManager.label_style())
        end_label.setMinimumWidth(80)
        time_layout.addWidget(end_label)
        
        self.end_time_input = QLineEdit()
        self.end_time_input.setPlaceholderText("HH:MM:SS (optional)")
        self.end_time_input.setStyleSheet(StyleManager.input_style())
        time_layout.addWidget(self.end_time_input, 1)
        download_layout.addLayout(time_layout)
        
        # Download settings
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(15)
        
        workers_label = QLabel("Workers:")
        workers_label.setStyleSheet(StyleManager.label_style())
        workers_label.setMinimumWidth(80)
        settings_layout.addWidget(workers_label)
        
        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setRange(1, 16)
        self.workers_spinbox.setValue(8)
        self.workers_spinbox.setStyleSheet(StyleManager.input_style())
        settings_layout.addWidget(self.workers_spinbox, 1)
        
        quality_label = QLabel("Quality:")
        quality_label.setStyleSheet(StyleManager.label_style())
        quality_label.setMinimumWidth(80)
        settings_layout.addWidget(quality_label)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["chunked", "720p60", "720p30", "480p30", "360p30", "160p30", "audio_only"])
        self.quality_combo.setStyleSheet(StyleManager.input_style())
        settings_layout.addWidget(self.quality_combo, 1)
        download_layout.addLayout(settings_layout)
        
        # Download buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.download_button = QPushButton("📥 Download")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setStyleSheet(StyleManager.button_style("#28a745", "#218838"))
        
        self.vlc_button = QPushButton("🎬 Play in VLC")
        self.vlc_button.clicked.connect(self.play_in_vlc)
        self.vlc_button.setStyleSheet(StyleManager.button_style("#ff6b35", "#e55a2b"))
        
        self.pause_button = QPushButton("⏸️ Pause")
        self.pause_button.clicked.connect(self.pause_download)
        self.pause_button.setStyleSheet(StyleManager.button_style("#ffc107", "#e0a800"))
        self.pause_button.setEnabled(False)
        
        self.stop_button = QPushButton("⏹️ Stop")
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setStyleSheet(StyleManager.button_style("#dc3545", "#c82333"))
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip("Stop download immediately")
        
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.vlc_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        download_layout.addLayout(button_layout)
        
        # Progress Section
        progress_group = QGroupBox("📊 Progress")
        progress_group.setStyleSheet(StyleManager.group_style())
        progress_group.setFixedHeight(120)
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(10)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(StyleManager.progress_style())
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # Speed label
        self.speed_label = QLabel("Speed: 0.00 MB/s")
        self.speed_label.setStyleSheet(StyleManager.label_style())
        progress_layout.addWidget(self.speed_label)
        
        # Console Section
        console_group = QGroupBox("📝 Console Output")
        console_group.setStyleSheet(StyleManager.group_style())
        console_layout = QVBoxLayout(console_group)
        console_layout.setSpacing(10)
        
        self.console_output = QTextEdit()
        self.console_output.setStyleSheet(StyleManager.console_style())
        self.console_output.setReadOnly(True)
        self.console_output.setMaximumHeight(200)
        console_layout.addWidget(self.console_output)
        
        # Add all groups to content layout
        content_layout.addWidget(finder_group)
        content_layout.addWidget(manual_group)
        content_layout.addWidget(download_group)
        content_layout.addWidget(progress_group)
        content_layout.addWidget(console_group)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Initialize console
        self.log_message("🚀 M3U8 Downloader initialized")
        self.log_message("💡 Paste a Streamscharts URL to automatically extract VOD info")
        self.log_message("🚨 Press Ctrl+Shift+S for emergency stop")
        
        # Add keyboard shortcut for emergency stop
        from PySide6.QtGui import QShortcut, QKeySequence
        emergency_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        emergency_shortcut.activated.connect(self.emergency_stop_all)
    
    def play_in_vlc(self):
        """Play the M3U8 URL directly in VLC"""
        url = self.url_input.text().strip()
        if not url:
            self.log_message("❌ Please enter an M3U8 URL first")
            return
        
        try:
            # Try to find VLC executable
            vlc_paths = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
                "/usr/bin/vlc",
                "/Applications/VLC.app/Contents/MacOS/VLC",
                "vlc"  # If VLC is in PATH
            ]
            
            vlc_exe = None
            for path in vlc_paths:
                if os.path.exists(path):
                    vlc_exe = path
                    break
            
            if not vlc_exe:
                # Try to run vlc from PATH
                vlc_exe = "vlc"
            
            # Launch VLC with the M3U8 URL
            subprocess.Popen([vlc_exe, url],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            
            self.log_message(f"🎬 Opening URL in VLC: {url}")
        
        except FileNotFoundError:
            self.log_message("❌ VLC not found. Please install VLC Media Player")
            QMessageBox.warning(
                self,
                "VLC Not Found",
                "VLC Media Player not found.\n\nPlease install VLC from:\nhttps://www.videolan.org/vlc/",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            self.log_message(f"❌ Error launching VLC: {str(e)}")
    
    def log_message(self, message):
        """Add message to console with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.console_output.append(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self.console_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.console_output.setTextCursor(cursor)
        
        # Process events to update UI
        QApplication.processEvents()
    
    def find_vod_m3u8(self):
        """Extract info from tracking URL and find VOD"""
        url = self.tracking_url_input.text().strip()
        if not url:
            self.log_message("❌ Please enter a tracking website URL")
            return
        
        # Disable button during extraction
        self.find_button.setEnabled(False)
        self.find_button.setText("🔍 Extracting...")
        
        # Start extraction thread
        self.extraction_thread = StreamInfoExtractionThread(url)
        self.extraction_thread.progress_update.connect(self.log_message)
        self.extraction_thread.extraction_finished.connect(self.on_extraction_finished)
        self.extraction_thread.start()
    
    def on_extraction_finished(self, streamer, vod_id, timestamp, error):
        """Handle extraction completion"""
        # Re-enable button
        self.find_button.setEnabled(True)
        self.find_button.setText("🔍 Extract Info")
        
        if error:
            self.log_message(f"⚠️ {error}")
        
        # Fill in the extracted info
        if streamer:
            self.streamer_input.setText(streamer)
            self.detected_streamer = streamer
            self.log_message(f"✅ Detected streamer: {streamer}")
        
        if vod_id:
            self.vod_id_input.setText(vod_id)
            self.log_message(f"✅ Detected VOD ID: {vod_id}")
        
        if timestamp:
            self.timestamp_input.setText(timestamp)
            self.log_message(f"✅ Detected timestamp: {timestamp}")
        
        # If we have all info, automatically find the VOD
        if streamer and vod_id:
            self.log_message("🔍 All info detected, searching for VOD...")
            self.find_vod_m3u8_manual()
        else:
            self.log_message("⚠️ Could not detect timestamp. Please enter manually.")
    
    def find_vod_m3u8_manual(self):
        """Find VOD M3U8 URL using manual input"""
        streamer = self.streamer_input.text().strip().lower()
        vod_id = self.vod_id_input.text().strip()
        timestamp = self.timestamp_input.text().strip()
        
        if not all([streamer, vod_id, timestamp]):
            self.log_message("❌ Please fill in streamer name, VOD ID, and timestamp")
            return
        
        # Validate VOD ID
        if not vod_id.isdigit() or len(vod_id) < 10:
            self.log_message("❌ VOD ID should be a number with at least 10 digits")
            return
        
        # Validate timestamp format
        try:
            datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            self.log_message("❌ Timestamp should be in format: YYYY-MM-DD HH:MM:SS")
            return
        
        # Disable buttons
        self.manual_find_button.setEnabled(False)
        self.manual_find_button.setText("🔍 Searching...")
        
        # Define domains to check
        domains = [
            "https://d2e2de1etea730.cloudfront.net/",
            "https://dqrpb9wgowsf5.cloudfront.net/",
            "https://ds0h3roq6wcgc.cloudfront.net/",
            "https://d2nvs31859zcd8.cloudfront.net/",
            "https://d2aba1wr3818hz.cloudfront.net/",
            "https://d3c27h4odz752x.cloudfront.net/",
            "https://dgeft87wbj63p.cloudfront.net/",
            "https://d1m7jfoe9zdc1j.cloudfront.net/",
            "https://d3vd9lfkzbru3h.cloudfront.net/",
            "https://d2vjef5jvl6bfs.cloudfront.net/",
            "https://d1ymi26ma8va5x.cloudfront.net/",
            "https://d1mhjrowxxagfy.cloudfront.net/",
            "https://ddacn6pr5v0tl.cloudfront.net/",
            "https://d3aqoihi2n8ty8.cloudfront.net/",
            "https://vod-secure.twitch.tv/",
            "https://vod-metro.twitch.tv/",
            "https://vod-pop-secure.twitch.tv/"
        ]
        
        # Start VOD finder thread
        self.vod_finder_thread = VODFinderThread(streamer, vod_id, timestamp, domains)
        self.vod_finder_thread.progress_update.connect(self.log_message)
        self.vod_finder_thread.found_url.connect(self.on_vod_found)
        self.vod_finder_thread.error.connect(self.on_vod_error)
        self.vod_finder_thread.start()
    
    def on_vod_found(self, url):
        """Handle successful VOD URL discovery"""
        self.manual_find_button.setEnabled(True)
        self.manual_find_button.setText("🔍 Find VOD")
        
        self.url_input.setText(url)
        self.log_message(f"✅ Found VOD URL: {url}")
        self.log_message("🎉 Ready to download! Configure settings and click Download.")
    
    def on_vod_error(self, error_msg):
        """Handle VOD finder errors"""
        self.manual_find_button.setEnabled(True)
        self.manual_find_button.setText("🔍 Find VOD")
        
        self.log_message(f"❌ {error_msg}")
        self.log_message("💡 Try adjusting the timestamp or check if the VOD is still available")
    
    def start_download(self):
        """Start the M3U8 download"""
        url = self.url_input.text().strip()
        if not url:
            self.log_message("❌ Please enter an M3U8 URL")
            return
        
        # Get or prompt for streamer name
        streamer_name = self.detected_streamer or self.streamer_input.text().strip()
        if not streamer_name:
            # Prompt user for streamer name
            streamer_name, ok = QInputDialog.getText(
                self,
                "Streamer Name Required",
                "Please enter the streamer name for the output folder:",
                QLineEdit.EchoMode.Normal,
                ""
            )
            if not ok or not streamer_name.strip():
                self.log_message("❌ Streamer name is required for download")
                return
            
            streamer_name = streamer_name.strip()
        
        # Update the streamer input field for future use
        self.streamer_input.setText(streamer_name)
        self.detected_streamer = streamer_name
        
        # Create output directory structure: Output/streamername/VODs
        output_dir = os.path.join("Output", FileNamingUtils.sanitize_filename(streamer_name), "VODs")
        
        # Create the directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
            self.log_message(f"📁 Created output directory: {output_dir}")
        except Exception as e:
            self.log_message(f"❌ Failed to create output directory: {str(e)}")
            return
        
        # Generate filename using FileNamingUtils
        default_filename = FileNamingUtils.generate_m3u8_vod_name(streamer_name)
        
        # Full path for the file - use this directly without dialog
        output_path = os.path.join(output_dir, default_filename)
        
        # Parse time inputs
        start_time_sec = None
        duration_sec = None
        start_time_str = self.start_time_input.text().strip()
        end_time_str = self.end_time_input.text().strip()
        
        if start_time_str:
            start_time_sec = TimeUtils.parse_time_string(start_time_str)
        
        if end_time_str and start_time_str:
            end_time_sec = TimeUtils.parse_time_string(end_time_str)
            if end_time_sec > start_time_sec:
                duration_sec = end_time_sec - start_time_sec
            else:
                self.log_message("❌ End time must be after start time")
                return
        
        # Get download settings
        max_workers = self.workers_spinbox.value()
        quality = self.quality_combo.currentText()
        
        # Modify URL for quality if not chunked
        if quality != "chunked":
            url = url.replace("/chunked/", f"/{quality}/")
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.speed_label.setText("Speed: 0.00 MB/s")
        
        # Update button states
        self.download_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        
        # Start download thread
        self.download_thread = FastM3U8DownloadThread(
            url, output_path, start_time_sec, duration_sec, max_workers
        )
        
        self.download_thread.progress_update.connect(self.log_message)
        self.download_thread.progress_value.connect(self.progress_bar.setValue)
        self.download_thread.speed_update.connect(self.update_speed)
        self.download_thread.download_finished.connect(self.on_download_finished)
        
        self.download_thread.start()
        
        self.log_message(f"🚀 Starting download with {max_workers} workers...")
        self.log_message(f"👤 Streamer: {streamer_name}")
        self.log_message(f"📁 Output: {output_path}")
        
        if start_time_sec is not None:
            self.log_message(f"⏰ Start time: {TimeUtils.format_seconds(start_time_sec)}")
        if duration_sec is not None:
            self.log_message(f"⏱️ Duration: {TimeUtils.format_seconds(duration_sec)}")
    
    def pause_download(self):
        """Pause/resume the download"""
        if self.download_thread and self.download_thread.isRunning():
            if self.download_thread.is_paused():
                self.download_thread.resume()
                self.pause_button.setText("⏸️ Pause")
            else:
                self.download_thread.pause()
                self.pause_button.setText("▶️ Resume")
    
    def stop_download(self):
        """Stop the download immediately"""
        if self.download_thread and self.download_thread.isRunning():
            self.log_message("⏹️ Stopping download immediately...")
            # Use abort for immediate stop
            self.download_thread.abort()
            
            # Update UI immediately
            self.download_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            self.pause_button.setText("⏸️ Pause")
            self.stop_button.setEnabled(False)
            
            # Force thread to stop within reasonable time
            if not self.download_thread.wait(5000):  # Wait 5 seconds
                self.log_message("⚠️ Force terminating download thread...")
                self.download_thread.terminate()
                self.download_thread.wait(2000)  # Wait for termination
    
    def update_speed(self, speed_text):
        """Update speed display"""
        self.speed_label.setText(f"Speed: {speed_text}")
        
        # Change color based on speed or just set a fixed color
        self.speed_label.setStyleSheet("""
            QLabel {
                color: #00ff00; /* Green */
                font-size: 13px;
                padding: 2px;
                font-weight: bold;
            }
        """)
    
    def emergency_stop_all(self):
        """Emergency stop all operations immediately"""
        self.log_message("🚨 EMERGENCY STOP - Terminating all operations...")
        
        # Stop all threads immediately
        if self.extraction_thread and self.extraction_thread.isRunning():
            self.extraction_thread.terminate()
        
        if self.vod_finder_thread and self.vod_finder_thread.isRunning():
            self.vod_finder_thread.terminate()
        
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
        
        # Reset UI
        self.download_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("⏸️ Pause")
        self.stop_button.setEnabled(False)
        self.find_button.setEnabled(True)
        self.find_button.setText("🔍 Extract Info")
        self.manual_find_button.setEnabled(True)
        self.manual_find_button.setText("🔍 Find VOD")
        
        self.log_message("🚨 Emergency stop completed")
    
    def on_download_finished(self, success, message):
        """Handle download completion"""
        # Reset button states
        self.download_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("⏸️ Pause")
        self.stop_button.setEnabled(False)
        
        if success:
            self.log_message(f"✅ {message}")
            self.progress_bar.setValue(100)
            
            # Show completion message
            QMessageBox.information(
                self,
                "Download Complete",
                f"VOD download completed successfully!\n\n{message}",
                QMessageBox.StandardButton.Ok
            )
        else:
            self.log_message(f"❌ {message}")
            
            # Show error message
            QMessageBox.warning(
                self,
                "Download Failed",
                f"VOD download failed:\n\n{message}",
                QMessageBox.StandardButton.Ok
            )
    
    def closeEvent(self, event):
        """Handle widget close event - ensure all threads are stopped"""
        self.log_message("🔄 Shutting down M3U8 Downloader...")
        
        # Stop extraction thread
        if self.extraction_thread and self.extraction_thread.isRunning():
            self.log_message("⏹️ Stopping extraction thread...")
            self.extraction_thread.stop()
            if not self.extraction_thread.wait(2000):
                self.log_message("⚠️ Extraction thread did not stop gracefully, terminating...")
                self.extraction_thread.terminate()
                self.extraction_thread.wait(1000)
        
        # Stop VOD finder thread
        if self.vod_finder_thread and self.vod_finder_thread.isRunning():
            self.log_message("⏹️ Stopping VOD finder thread...")
            self.vod_finder_thread.stop()
            if not self.vod_finder_thread.wait(2000):
                self.log_message("⚠️ VOD finder thread did not stop gracefully, terminating...")
                self.vod_finder_thread.terminate()
                self.vod_finder_thread.wait(1000)
        
        # Stop download thread
        if self.download_thread and self.download_thread.isRunning():
            self.log_message("⏹️ Stopping download thread immediately...")
            self.download_thread.abort()
            
            if not self.download_thread.wait(2000):
                self.log_message("⚠️ Download thread did not stop gracefully, terminating...")
                self.download_thread.terminate()
                self.download_thread.wait(1000)
        
        # Clean up any remaining thread references
        self.extraction_thread = None
        self.vod_finder_thread = None
        self.download_thread = None
        
        self.log_message("✅ M3U8 Downloader shutdown complete")
        event.accept()
    
    def __del__(self):
        """Destructor - no cleanup"""
        try:
            # Stop all threads if they're still running
            if hasattr(self, 'extraction_thread') and self.extraction_thread and self.extraction_thread.isRunning():
                self.extraction_thread.stop()
                self.extraction_thread.wait(500)
                if self.extraction_thread.isRunning():
                    self.extraction_thread.terminate()
            
            if hasattr(self, 'vod_finder_thread') and self.vod_finder_thread and self.vod_finder_thread.isRunning():
                self.vod_finder_thread.stop()
                self.vod_finder_thread.wait(500)
                if self.vod_finder_thread.isRunning():
                    self.vod_finder_thread.terminate()
            
            if hasattr(self, 'download_thread') and self.download_thread and self.download_thread.isRunning():
                self.download_thread.abort()
                self.download_thread.wait(1000)
                if self.download_thread.isRunning():
                    self.download_thread.terminate()
        
        except Exception:
            pass  # Ignore errors in destructor     