import requests
import time
import logging
from datetime import datetime
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ping_bot.log'),
        logging.StreamHandler()
    ]
)

class PingBot:
    def __init__(self, url, interval=120):
        """
        Initialize the ping bot
        
        Args:
            url (str): The URL to monitor
            interval (int): Check interval in seconds (default: 120 = 2 minutes)
        """
        self.url = url
        self.interval = interval
        self.previous_status = None
        self.session = requests.Session()
        
        # Set a reasonable timeout for requests
        self.session.timeout = 30
        
    def check_status(self):
        """
        Check the status of the target URL
        
        Returns:
            dict: Dictionary containing status_code and response_time, or None if request failed
        """
        try:
            start_time = time.time()
            response = self.session.get(self.url)
            response_time = round((time.time() - start_time) * 1000, 2)  # Convert to milliseconds
            
            return {
                'status_code': response.status_code,
                'response_time': response_time,
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed for {self.url}: {e}")
            return None
    
    def log_status_change(self, current_result, previous_result):
        """
        Log when status changes
        
        Args:
            current_result (dict): Current monitoring result
            previous_result (dict): Previous monitoring result
        """
        if current_result is None:
            logging.error(f"Failed to get status for {self.url}")
            return
            
        current_status = current_result['status_code']
        current_time = current_result['response_time']
        
        if previous_result is None:
            logging.info(f"Initial status check for {self.url}: {current_status} (Response time: {current_time}ms)")
        else:
            previous_status = previous_result['status_code']
            if current_status != previous_status:
                logging.warning(f"Status changed for {self.url} from {previous_status} to {current_status} (Response time: {current_time}ms)")
            else:
                logging.info(f"Status unchanged for {self.url}: {current_status} (Response time: {current_time}ms)")
    
    def run(self):
        """
        Run the monitoring loop
        """
        logging.info(f"Starting ping bot for {self.url}")
        logging.info(f"Check interval: {self.interval} seconds")
        
        try:
            while True:
                current_result = self.check_status()
                
                if current_result is not None:
                    self.log_status_change(current_result, self.previous_status)
                    self.previous_status = current_result
                else:
                    logging.error(f"Failed to get status code for {self.url}")
                
                logging.info(f"Next check for {self.url} in {self.interval} seconds...")
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            logging.info(f"Ping bot stopped by user for {self.url}")
        except Exception as e:
            logging.error(f"Unexpected error for {self.url}: {e}")

class MultiURLPingBot:
    def __init__(self):
        """
        Initialize multi-URL ping bot
        """
        self.bots = {}
        self.results_file = 'monitoring_results.json'
        
    def add_url(self, url, interval=120):
        """
        Add a URL to monitor
        
        Args:
            url (str): URL to monitor
            interval (int): Check interval in seconds
        """
        self.bots[url] = PingBot(url, interval)
        
    def remove_url(self, url):
        """
        Remove a URL from monitoring
        
        Args:
            url (str): URL to remove
        """
        if url in self.bots:
            del self.bots[url]
            
    def check_all_urls(self):
        """
        Check all URLs once
        
        Returns:
            dict: Results for all URLs
        """
        results = {}
        for url, bot in self.bots.items():
            result = bot.check_status()
            if result:
                results[url] = result
                bot.log_status_change(result, bot.previous_status)
                bot.previous_status = result
            else:
                results[url] = None
                
        # Save results to file for dashboard
        self.save_results(results)
        return results
    
    def save_results(self, results):
        """
        Save monitoring results to file
        
        Args:
            results (dict): Monitoring results
        """
        try:
            # Load existing results
            if os.path.exists(self.results_file):
                with open(self.results_file, 'r') as f:
                    all_results = json.load(f)
            else:
                all_results = {}
            
            # Add new results with timestamp
            timestamp = datetime.now().isoformat()
            all_results[timestamp] = results
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(all_results) > 1000:
                # Remove oldest entries
                timestamps = sorted(all_results.keys())
                for old_timestamp in timestamps[:-1000]:
                    del all_results[old_timestamp]
            
            # Save back to file
            with open(self.results_file, 'w') as f:
                json.dump(all_results, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving results: {e}")
    
    def get_recent_results(self, hours=24):
        """
        Get recent monitoring results
        
        Args:
            hours (int): Number of hours to look back
            
        Returns:
            dict: Recent results organized by URL
        """
        try:
            if not os.path.exists(self.results_file):
                return {}
                
            with open(self.results_file, 'r') as f:
                all_results = json.load(f)
            
            # Filter results from last N hours
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            recent_results = {}
            
            for timestamp, results in all_results.items():
                try:
                    result_time = datetime.fromisoformat(timestamp).timestamp()
                    if result_time >= cutoff_time:
                        for url, result in results.items():
                            if url not in recent_results:
                                recent_results[url] = []
                            recent_results[url].append({
                                'timestamp': timestamp,
                                'result': result
                            })
                except:
                    continue
            
            return recent_results
            
        except Exception as e:
            logging.error(f"Error loading recent results: {e}")
            return {}

def main():
    """
    Main function to run the ping bot
    """
    # Configuration
    TARGET_URL = "https://example.com"  # Change this to your target URL
    CHECK_INTERVAL = 120  # 2 minutes in seconds
    
    # Create and run the bot
    bot = PingBot(TARGET_URL, CHECK_INTERVAL)
    bot.run()

if __name__ == "__main__":
    main() 