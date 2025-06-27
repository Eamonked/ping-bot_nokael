from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import threading
import time
import logging
from ping_bot import MultiURLPingBot
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration file
CONFIG_FILE = 'bot_config.json'

# Global variables
bot_thread = None
multi_bot = MultiURLPingBot()
bot_running = False

def load_config():
    """Load configuration from file"""
    default_config = {
        'urls': [
            {
                'url': 'https://example.com',
                'interval': 120,
                'enabled': True
            }
        ],
        'enabled': False
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                
            # Ensure the config has the new structure
            if 'urls' not in loaded_config:
                # Convert old single-URL format to new multi-URL format
                if 'target_url' in loaded_config:
                    loaded_config['urls'] = [
                        {
                            'url': loaded_config['target_url'],
                            'interval': loaded_config.get('check_interval', 120),
                            'enabled': True
                        }
                    ]
                    # Remove old keys
                    loaded_config.pop('target_url', None)
                    loaded_config.pop('check_interval', None)
                else:
                    # If no URLs found, use default
                    loaded_config['urls'] = default_config['urls']
            
            # Ensure all required fields exist
            for url_config in loaded_config['urls']:
                if 'url' not in url_config:
                    url_config['url'] = 'https://example.com'
                if 'interval' not in url_config:
                    url_config['interval'] = 120
                if 'enabled' not in url_config:
                    url_config['enabled'] = True
            
            if 'enabled' not in loaded_config:
                loaded_config['enabled'] = False
                
            return loaded_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config
    return default_config

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def run_bot():
    """Run the bot in a separate thread"""
    global multi_bot, bot_running
    
    config = load_config()
    bot_running = True
    
    # Clear existing bots and add new ones
    multi_bot.bots.clear()
    for url_config in config['urls']:
        if url_config.get('enabled', True):
            multi_bot.add_url(url_config['url'], url_config['interval'])
    
    # Get the minimum interval for the main loop
    min_interval = min([url_config.get('interval', 120) for url_config in config['urls'] if url_config.get('enabled', True)], default=120)
    
    try:
        while bot_running:
            # Check all URLs
            multi_bot.check_all_urls()
            
            # Sleep for the minimum interval
            for _ in range(min_interval):
                if not bot_running:
                    break
                time.sleep(1)
                
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        bot_running = False

@app.route('/')
def dashboard():
    """Main dashboard page"""
    try:
        config = load_config()
        return render_template('dashboard.html', config=config, bot_running=bot_running)
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        # Return a minimal config if there's an error
        fallback_config = {
            'urls': [{'url': 'https://example.com', 'interval': 120, 'enabled': True}],
            'enabled': False
        }
        return render_template('dashboard.html', config=fallback_config, bot_running=bot_running)

@app.route('/update_config', methods=['POST'])
def update_config():
    """Update bot configuration"""
    global bot_thread, bot_running
    
    config = load_config()
    
    # Parse form data for multiple URLs
    urls = []
    url_count = int(request.form.get('url_count', 1))
    
    for i in range(url_count):
        url = request.form.get(f'url_{i}', '').strip()
        interval = int(request.form.get(f'interval_{i}', 120))
        enabled = request.form.get(f'enabled_{i}') == 'on'
        
        if url:  # Only add non-empty URLs
            urls.append({
                'url': url,
                'interval': interval,
                'enabled': enabled
            })
    
    config['urls'] = urls
    config['enabled'] = request.form.get('enabled') == 'on'
    
    save_config(config)
    
    # Always stop the bot if running
    if bot_running:
        bot_running = False
        if bot_thread:
            bot_thread.join(timeout=5)
    
    # Start bot if enabled
    if config['enabled']:
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
    
    return redirect(url_for('dashboard'))

@app.route('/api/status')
def api_status():
    """API endpoint to get bot status"""
    config = load_config()
    return jsonify({
        'running': bot_running,
        'config': config
    })

@app.route('/api/logs')
def api_logs():
    """API endpoint to get recent logs"""
    try:
        with open('ping_bot.log', 'r') as f:
            lines = f.readlines()
            # Return last 50 lines
            return jsonify({'logs': lines[-50:]})
    except FileNotFoundError:
        return jsonify({'logs': []})

@app.route('/api/results')
def api_results():
    """API endpoint to get monitoring results for charts"""
    hours = int(request.args.get('hours', 24))
    results = multi_bot.get_recent_results(hours)
    
    # Format data for Chart.js
    chart_data = {}
    for url, url_results in results.items():
        chart_data[url] = {
            'labels': [],
            'response_times': [],
            'status_codes': []
        }
        
        for entry in url_results:
            if entry['result'] is None:
                continue
            timestamp = datetime.fromisoformat(entry['timestamp'])
            chart_data[url]['labels'].append(timestamp.strftime('%H:%M'))
            chart_data[url]['response_times'].append(entry['result']['response_time'])
            chart_data[url]['status_codes'].append(entry['result']['status_code'])
    
    return jsonify(chart_data)

@app.route('/api/current_status')
def api_current_status():
    """API endpoint to get current status of all URLs"""
    try:
        config = load_config()
        current_status = {}
        
        # Ensure we have a valid URLs list
        urls = config.get('urls', [])
        if not urls:
            return jsonify({})
        
        for url_config in urls:
            url = url_config.get('url', '')
            if not url:
                continue
                
            if url in multi_bot.bots:
                bot = multi_bot.bots[url]
                current_status[url] = {
                    'previous_result': bot.previous_status,
                    'enabled': url_config.get('enabled', True),
                    'interval': url_config.get('interval', 120)
                }
            else:
                current_status[url] = {
                    'previous_result': None,
                    'enabled': url_config.get('enabled', True),
                    'interval': url_config.get('interval', 120)
                }
        
        return jsonify(current_status)
    except Exception as e:
        print(f"Error in api_current_status: {e}")
        return jsonify({})

@app.route('/api/update_url', methods=['POST'])
def api_update_url():
    """API endpoint to update a single URL via AJAX"""
    global bot_thread, bot_running
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        original_url = data.get('original_url', '').strip()
        new_url = data.get('url', '').strip()
        interval = int(data.get('interval', 120))
        enabled = data.get('enabled', True)
        
        if not new_url:
            return jsonify({'success': False, 'error': 'URL cannot be empty'}), 400
        
        config = load_config()
        
        # Find and update the URL in the config
        url_updated = False
        for url_config in config['urls']:
            if url_config.get('url', '') == original_url:
                url_config['url'] = new_url
                url_config['interval'] = interval
                url_config['enabled'] = enabled
                url_updated = True
                break
        
        if not url_updated:
            return jsonify({'success': False, 'error': 'URL not found'}), 404
        
        save_config(config)
        
        # Restart bot if running to pick up changes
        if bot_running:
            bot_running = False
            if bot_thread:
                bot_thread.join(timeout=5)
        
        if config['enabled']:
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'URL updated successfully',
            'config': config
        })
        
    except Exception as e:
        print(f"Error updating URL: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add_url', methods=['POST'])
def api_add_url():
    """API endpoint to add a new URL via AJAX"""
    global bot_thread, bot_running
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        url = data.get('url', '').strip()
        interval = int(data.get('interval', 120))
        enabled = data.get('enabled', True)
        
        if not url:
            return jsonify({'success': False, 'error': 'URL cannot be empty'}), 400
        
        config = load_config()
        
        # Check if URL already exists
        for url_config in config['urls']:
            if url_config.get('url', '') == url:
                return jsonify({'success': False, 'error': 'URL already exists'}), 409
        
        # Add new URL
        new_url_config = {
            'url': url,
            'interval': interval,
            'enabled': enabled
        }
        config['urls'].append(new_url_config)
        
        save_config(config)
        
        # Restart bot if running to pick up new URL
        if bot_running:
            bot_running = False
            if bot_thread:
                bot_thread.join(timeout=5)
        
        if config['enabled']:
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'URL added successfully',
            'config': config,
            'new_url_index': len(config['urls']) - 1
        })
        
    except Exception as e:
        print(f"Error adding URL: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/remove_url', methods=['POST'])
def api_remove_url():
    """API endpoint to remove a URL via AJAX"""
    global bot_thread, bot_running
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'URL cannot be empty'}), 400
        
        config = load_config()
        
        # Remove URL from config
        original_count = len(config['urls'])
        config['urls'] = [url_config for url_config in config['urls'] if url_config.get('url', '') != url]
        
        if len(config['urls']) == original_count:
            return jsonify({'success': False, 'error': 'URL not found'}), 404
        
        save_config(config)
        
        # Restart bot if running to pick up changes
        if bot_running:
            bot_running = False
            if bot_thread:
                bot_thread.join(timeout=5)
        
        if config['enabled']:
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'URL removed successfully',
            'config': config
        })
        
    except Exception as e:
        print(f"Error removing URL: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Get port from environment variable or default to 5001
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Start the Flask app
    print("Starting Ping Bot Dashboard...")
    print(f"Open your browser to: http://{host}:{port}")
    app.run(debug=False, host=host, port=port)