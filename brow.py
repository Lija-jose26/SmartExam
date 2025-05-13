import time
import psutil
import win32gui
import win32process
import win32con
from datetime import datetime, timezone
import os
import hashlib
import logging
import threading
import re
from urllib.parse import urlparse
from tabulate import tabulate
import csv

class BrowserActivityTracker:
    def __init__(self):
        self.activities = {}  # Dictionary to store activities per student/exam
        self.start_times = {}  # Dictionary to store start times per student/exam
        self.tracking_active = {}  # Track active monitoring sessions
        self.supported_browsers = {
            'chrome.exe': 'Google Chrome',
            'msedge.exe': 'Microsoft Edge',
            'firefox.exe': 'Firefox',
            'opera.exe': 'Opera',
            'brave.exe': 'Brave'
        }
        self.monitoring_threads = {}  # Store monitoring threads
        self.last_window_titles = {}  # Track last window titles to avoid duplicates
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler("browser_tracker.log"), logging.StreamHandler()]
        )
        self.logger = logging.getLogger("BrowserTracker")

    def get_session_key(self, student_id, exam_id):
        """Generate unique key for storing student exam session data"""
        return f"{student_id}_{exam_id}"

    def start_tracking(self, student_id, exam_id):
        """Start tracking browser activity for specific student and exam"""
        session_key = self.get_session_key(student_id, exam_id)
        self.start_times[session_key] = datetime.now(timezone.utc)
        self.activities[session_key] = []
        self.tracking_active[session_key] = True
        self.last_window_titles[session_key] = {}
        
        # Start continuous monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_browsers_continuously,
            args=(student_id, exam_id),
            daemon=True
        )
        self.monitoring_threads[session_key] = monitor_thread
        monitor_thread.start()
        
        self.logger.info(f"Started browser tracking for student {student_id}, exam {exam_id}")
        return True

    def _find_browser_processes(self):
        """Find all active browser processes"""
        browser_processes = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process_name = proc.info['name'].lower()
                for browser_name in self.supported_browsers.keys():
                    if browser_name.lower() == process_name:
                        browser_processes.append({
                            'pid': proc.info['pid'],
                            'name': process_name,
                            'browser_display_name': self.supported_browsers[browser_name]
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return browser_processes

    def _get_window_title_and_process(self, hwnd, extra):
        """Callback function for EnumWindows"""
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.IsIconic(hwnd):  # Skip minimized windows
            return
            
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
            
        # Get process ID for this window
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            extra.append((hwnd, title, pid))
        except Exception:
            pass
            
    def _get_all_browser_windows(self):
        """Get all visible browser windows"""
        windows = []
        win32gui.EnumWindows(self._get_window_title_and_process, windows)
        
        # Get all browser processes
        browser_processes = self._find_browser_processes()
        browser_pids = {proc['pid']: proc for proc in browser_processes}
        
        # Filter windows that belong to browsers
        browser_windows = []
        for hwnd, title, pid in windows:
            if pid in browser_pids:
                browser_info = browser_pids[pid]
                browser_windows.append({
                    'hwnd': hwnd,
                    'title': title,
                    'pid': pid,
                    'browser_name': browser_info['browser_display_name']
                })
                
        return browser_windows

    def _parse_browser_title(self, browser_name, window_title):
        """Extract URL and page title from browser window title"""
        url = None
        title = window_title
        
        # Chrome/Edge/Brave typically show "Page Title - Browser"
        if any(b in browser_name for b in ['Chrome', 'Edge', 'Brave', 'Opera']):
            # Try to extract site from title
            if ' - ' in window_title and not window_title.endswith(' - ' + browser_name):
                title = window_title.split(' - ')[0].strip()
                # Check if title looks like a URL
                if '://' in title:
                    url = title
                    title = window_title
                    
        # Firefox typically shows "Page Title — Mozilla Firefox"
        elif 'Firefox' in browser_name:
            if ' — Mozilla Firefox' in window_title:
                title = window_title.replace(' — Mozilla Firefox', '').strip()
                
        # For exam systems running in browsers, look for patterns like http://127.0.0.1:5003/attend_exam
        # Try to extract URLs from titles
        url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+\.[a-zA-Z]{2,}[^\s]*'
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, window_title)
            if matches:
                url = matches[0]
                break
                
        # If we found a title but no URL, make a guess based on title
        if not url and title:
            # Common pattern: if title is "Site Name", guess it's site-name.com
            simplified_title = ''.join(c.lower() for c in title if c.isalnum())
            if simplified_title and len(simplified_title) > 3:
                url = f"http://{simplified_title}.com"  # Best-effort URL guess
        
        return {
            'url': url,
            'title': title,
            'window_title': window_title,
            'browser_name': browser_name
        }

    def _get_active_window_info(self):
        """Get information about the currently active window"""
        try:
            active_hwnd = win32gui.GetForegroundWindow()
            if active_hwnd:
                window_title = win32gui.GetWindowText(active_hwnd)
                if window_title:
                    _, pid = win32process.GetWindowThreadProcessId(active_hwnd)
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name()
                        
                        # Check if this is a browser
                        browser_name = None
                        for browser_exe, browser_display_name in self.supported_browsers.items():
                            if browser_exe.lower() == process_name.lower():
                                browser_name = browser_display_name
                                break
                                
                        if browser_name:
                            return {
                                'hwnd': active_hwnd,
                                'title': window_title,
                                'pid': pid,
                                'browser_name': browser_name,
                                'is_active': True
                            }
                    except psutil.NoSuchProcess:
                        pass
        except Exception as e:
            self.logger.error(f"Error getting active window: {str(e)}")
            
        return None

    def _monitor_browsers_continuously(self, student_id, exam_id):
        """Continuously monitor all active browser windows and tabs"""
        session_key = self.get_session_key(student_id, exam_id)
        
        while self.tracking_active.get(session_key, False):
            try:
                # Get all browser windows
                browser_windows = self._get_all_browser_windows()
                
                # Get active window (for prioritizing)
                active_window = self._get_active_window_info()
                
                # Process windows, starting with active window if it's a browser
                if active_window:
                    # Process active window first (highest priority)
                    window_info = self._parse_browser_title(
                        active_window['browser_name'], 
                        active_window['title']
                    )
                    
                    # Combine window info
                    window_info.update({
                        'hwnd': active_window['hwnd'],
                        'pid': active_window['pid'],
                        'is_active': True
                    })
                    
                    # Generate a unique window identifier
                    window_id = f"{active_window['pid']}_{active_window['hwnd']}"
                    
                    # Only record if window title changed
                    prev_title = self.last_window_titles[session_key].get(window_id)
                    if prev_title != active_window['title']:
                        self.record_activity(
                            student_id=student_id,
                            exam_id=exam_id,
                            url=window_info['url'],
                            title=f"{window_info['browser_name']}: {window_info['title']}"
                        )
                        self.last_window_titles[session_key][window_id] = active_window['title']
                
                # Process all other browser windows
                for window in browser_windows:
                    # Skip if this is the already processed active window
                    if active_window and window['hwnd'] == active_window['hwnd']:
                        continue
                        
                    window_info = self._parse_browser_title(
                        window['browser_name'], 
                        window['title']
                    )
                    
                    # Combine window info
                    window_info.update({
                        'hwnd': window['hwnd'],
                        'pid': window['pid'],
                        'is_active': False
                    })
                    
                    # Generate a unique window identifier
                    window_id = f"{window['pid']}_{window['hwnd']}"
                    
                    # Only record if window title changed
                    prev_title = self.last_window_titles[session_key].get(window_id)
                    if prev_title != window['title']:
                        self.record_activity(
                            student_id=student_id,
                            exam_id=exam_id,
                            url=window_info['url'],
                            title=f"{window_info['browser_name']}: {window_info['title']}"
                        )
                        self.last_window_titles[session_key][window_id] = window['title']
                
            except Exception as e:
                self.logger.error(f"Error monitoring browsers: {str(e)}")
            
            # Wait before next check - balance between responsiveness and resource usage
            time.sleep(1)

    def record_activity(self, student_id, exam_id, url, title, timestamp=None):
        """Record a browser activity for specific student and exam"""
        session_key = self.get_session_key(student_id, exam_id)

        if session_key not in self.activities:
            self.start_tracking(student_id, exam_id)

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Add more detailed information about the URL
        domain = "Unknown Domain"
        path = ""
        if url:
            try:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc if parsed_url.netloc else "Unknown Domain"
                path = parsed_url.path
            except:
                pass

        activity = {
            'timestamp': timestamp,
            'url': url if url else "Unknown URL",
            'domain': domain,
            'title': title,
            'path': path
        }
        
        self.activities[session_key].append(activity)
        self.logger.info(f"Recorded activity: {domain} - {title}")

    def stop_tracking(self, student_id, exam_id):
        """Stop tracking browser activity for specific student and exam"""
        session_key = self.get_session_key(student_id, exam_id)
        self.tracking_active[session_key] = False
        
        # Wait for monitoring thread to terminate
        if session_key in self.monitoring_threads:
            self.monitoring_threads[session_key].join(timeout=2.0)
            del self.monitoring_threads[session_key]
        
        self.logger.info(f"Stopped browser tracking for student {student_id}, exam {exam_id}")

    def generate_unique_filename(self, student_id, exam_id):
        """Generate unique filename for the CSV report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_hash = hashlib.md5(f"{student_id}_{exam_id}_{timestamp}".encode()).hexdigest()[:8]
        return f"browser_activity_student_{student_id}_exam_{exam_id}_{timestamp}_{unique_hash}.csv"

    def generate_pdf_report(self, student_id, exam_id):
        """Generate CSV report of browser activity for specific student and exam"""
        session_key = self.get_session_key(student_id, exam_id)

        if session_key not in self.activities or not self.activities[session_key]:
            return None

        # Create base directory structure
        base_dir = 'static/browser_reports'
        student_dir = f"{base_dir}/student_{student_id}"
        exam_dir = f"{student_dir}/exam_{exam_id}"

        os.makedirs(exam_dir, exist_ok=True)

        filename = self.generate_unique_filename(student_id, exam_id)
        full_path = f"{exam_dir}/{filename}"

        try:
            with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Time', 'Browser/Title', 'Domain', 'Full URL']
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(fieldnames)
                
                # Write data rows
                for activity in sorted(self.activities[session_key], key=lambda x: x['timestamp']):
                    local_time = activity['timestamp'].astimezone().strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow([
                        local_time,
                        activity['title'],
                        activity['domain'],
                        activity['url']
                    ])

            self.logger.info(f"CSV report generated successfully: {full_path}")
            return full_path
        except Exception as e:
            self.logger.error(f"Error generating CSV report: {str(e)}")
            return None

    def display_activities(self, student_id, exam_id):
        """Display activities in a readable format using tabulate"""
        session_key = self.get_session_key(student_id, exam_id)
        if session_key not in self.activities or not self.activities[session_key]:
            print("No activities recorded for this session.")
            return

        headers = ["Time", "Browser/Title", "Domain", "Full URL"]
        table_data = []
        for activity in sorted(self.activities[session_key], key=lambda x: x['timestamp']):
            local_time = activity['timestamp'].astimezone().strftime('%Y-%m-%d %H:%M:%S')
            table_data.append([
                local_time,
                activity['title'],
                activity['domain'],
                activity['url']
            ])

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

# Usage example
if __name__ == "__main__":
    browser_tracker = BrowserActivityTracker()
    browser_tracker.start_tracking("student123", "exam456")
    print("Tracking started. Press Ctrl+C to stop and generate report...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        browser_tracker.stop_tracking("student123", "exam456")
        browser_tracker.generate_csv_report("student123", "exam456")