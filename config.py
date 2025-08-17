import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ==================== CONFIGURATION SECTION ====================

def load_config():
    """Load configuration from JSON file"""
    try:
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        config_path = script_dir / 'trading_config.json'

        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ trading_config.json not found!")
        # Create a default config if it doesn't exist
        default_config = {
            "metadata": {"version": "2.0.0"},
            "exchange": {"websocket_url": "wss://ws-api.coindcx.com/v1/sub"},
            "websocket": {"timeout": 60, "ping_interval": 10},
            "trading_pairs": {"default_pairs": [
                {"symbol": "BTC/USDT", "channel": "B-BTC_USDT@prices-futures", "enabled": True, "quantity_precision": 3},
                {"symbol": "ETH/USDT", "channel": "B-ETH_USDT@prices-futures", "enabled": True, "quantity_precision": 3}
            ]},
            "server": {"host": "0.0.0.0", "port": 8000, "debug": True, "auto_open_browser": True},
            "ui_settings": {"update_interval_ms": 1000},
            "risk_management": {"take_profit": {"percentage": 5.0}, "stop_loss": {"percentage": 50.0}},
            "leverage": {"default": 10.0, "min": 1.0, "max": 15.0},
            "trading_parameters": {"quick_trade_amount": 10.0, "min_order_value_usdt": 6.0, "default_order_type": "limit_order", "notification_preference": "no_notification", "default_time_in_force": "good_till_cancel"},
            "features": {"auto_tpsl": {"enabled": True}}
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"✅ Created default trading_config.json at {config_path}")
        return default_config
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in trading_config.json: {e}")
        raise

# Load centralized configuration (before logger is defined)
CONFIG = load_config()

# CoinDCX API Configuration (from environment or config)
COINDCX_API_KEY = os.getenv("COINDCX_API_KEY", "b3605433341a2df4677cbf8cf3dda0f8c52de1b09a273fd8")
COINDCX_SECRET_KEY = os.getenv("COINDCX_SECRET_KEY", "1b59f868cd3cbfd8ab616de96645b1267a6729c5dc238dc6144c76da14129ce7")

# Configuration from JSON
COINDCX_WEBSOCKET_URL = CONFIG["exchange"]["websocket_url"]
WEBSOCKET_TIMEOUT = CONFIG["websocket"]["timeout"]
PING_INTERVAL = CONFIG["websocket"]["ping_interval"]

# Trading Pairs from Configuration
TRADING_PAIRS = [pair["symbol"] for pair in CONFIG["trading_pairs"]["default_pairs"] if pair["enabled"]]
COINDCX_CHANNELS = [pair["channel"] for pair in CONFIG["trading_pairs"]["default_pairs"] if pair["enabled"]]

# Server Configuration from JSON
SERVER_HOST = CONFIG["server"]["host"]
SERVER_PORT = CONFIG["server"]["port"]
DEBUG = CONFIG["server"]["debug"]
AUTO_OPEN_BROWSER = CONFIG["server"].get("auto_open_browser", True)

# Dashboard Configuration from JSON
DASHBOARD_TITLE = f"CoinDCX Trading Dashboard v{CONFIG['metadata']['version']}"
UPDATE_INTERVAL = CONFIG["ui_settings"]["update_interval_ms"]

# Price Data Storage
PRICE_DATA = {}

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper functions to access configuration
def get_pair_config(symbol: str) -> Optional[Dict]:
    """Get configuration for a specific trading pair"""
    for pair in CONFIG["trading_pairs"]["default_pairs"]:
        if pair["symbol"] == symbol:
            return pair
    return None

def get_risk_management_config() -> Dict:
    """Get risk management configuration"""
    return CONFIG["risk_management"]

def get_leverage_config() -> Dict:
    """Get leverage configuration"""
    return CONFIG["leverage"]

def get_trading_params() -> Dict:
    """Get trading parameters"""
    return CONFIG["trading_parameters"]

def calculate_tp_sl(desired_tp: float, desired_sl: float, leverage: float = 10.0) -> Tuple[Optional[float], Optional[float]]:
    """
    Enhanced SL/TP calculation with flexible percentages and proper validation
    """
    try:
        if leverage <= 0:
            logger.error("❌ Leverage must be greater than 0.")
            return None, None
        if desired_tp < 0 or desired_sl < 0:
            logger.error("❌ Take Profit and Stop Loss percentages must be non-negative.")
            return None, None
        if desired_tp > 1000 or desired_sl > 1000:
            logger.error("❌ TP/SL percentages seem unreasonably high (>1000%).")
            return None, None
        position_tp_percent = desired_tp / leverage
        position_sl_percent = desired_sl / leverage
        position_tp_decimal = position_tp_percent / 100
        position_sl_decimal = position_sl_percent / 100
        logger.debug(f"🧮 SL/TP Calculation: TP={desired_tp}%/{leverage}x = {position_tp_decimal:.6f}, SL={desired_sl}%/{leverage}x = {position_sl_decimal:.6f}")
        return position_tp_decimal, position_sl_decimal
    except (ValueError, TypeError) as e:
        logger.error(f"❌ Invalid input for TP/SL calculation: {e}")
        return None, None

def get_symbol_from_channel(channel: str) -> str:
    """
    Convert CoinDCX channel format to display symbol
    """
    if "@prices-futures" in channel:
        symbol_part = channel.replace("@prices-futures", "").replace("B-", "")
        return symbol_part.replace("_", "/")
    return channel

def get_channel_from_symbol(symbol: str) -> str:
    """
    Convert display symbol to CoinDCX channel format
    """
    channel_symbol = symbol.replace("/", "_")
    return f"B-{channel_symbol}@prices-futures"

def validate_config():
    """Validate configuration settings"""
    if COINDCX_API_KEY == "your_api_key_here":
        print("⚠️  WARNING: Please set your CoinDCX API key in config.py or environment variables")
    if COINDCX_SECRET_KEY == "your_secret_key_here":
        print("⚠️  WARNING: Please set your CoinDCX secret key in config.py or environment variables")
    print(f"✅ Configuration loaded:")
    print(f"   - Trading pairs: {len(TRADING_PAIRS)}")
    print(f"   - WebSocket channels: {len(COINDCX_CHANNELS)}")
    print(f"   - Server: {SERVER_HOST}:{SERVER_PORT}")

# ==================== CONFIGURATION MANAGEMENT SYSTEM ====================

class ConfigurationFileHandler(FileSystemEventHandler):
    """File system event handler for configuration file changes"""
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('trading_config.json'):
            logger.info("📝 Configuration file changed, reloading...")
            self.config_manager.reload_configuration()

class ConfigurationManager:
    """Centralized configuration management with hot-reload capability"""
    def __init__(self, config_path: str = "trading_config.json"):
        script_dir = Path(__file__).parent
        self.config_path = script_dir / config_path
        self.config = {}
        self.observers = []
        self.file_observer = None
        self.reload_callbacks = []
        self.load_configuration()
        self.setup_file_watcher()

    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from JSON file with validation"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            if self.validate_configuration(new_config):
                self.config = new_config
                logger.info(f"✅ Configuration loaded from {self.config_path}")
                return self.config
            else:
                logger.error("❌ Configuration validation failed")
                return self.config
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading configuration: {e}")
            raise

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure and values"""
        try:
            required_sections = [
                'metadata', 'exchange', 'trading_pairs', 'risk_management',
                'leverage', 'trading_parameters', 'ui_settings', 'server'
            ]
            for section in required_sections:
                if section not in config:
                    logger.error(f"❌ Missing required configuration section: {section}")
                    return False
            if not config['trading_pairs'].get('default_pairs'):
                logger.error("❌ No trading pairs configured")
                return False
            risk_mgmt = config['risk_management']
            if not all(key in risk_mgmt for key in ['take_profit', 'stop_loss']):
                logger.error("❌ Invalid risk management configuration")
                return False
            leverage = config['leverage']
            if not all(key in leverage for key in ['default', 'min', 'max']):
                logger.error("❌ Invalid leverage configuration")
                return False
            if leverage['min'] > leverage['max'] or leverage['default'] < leverage['min'] or leverage['default'] > leverage['max']:
                logger.error("❌ Invalid leverage range")
                return False
            logger.info("✅ Configuration validation passed")
            return True
        except Exception as e:
            logger.error(f"❌ Configuration validation error: {e}")
            return False

    def save_configuration(self, config: Dict[str, Any] = None) -> bool:
        """Save configuration to JSON file"""
        try:
            config_to_save = config or self.config
            config_to_save['metadata']['last_updated'] = datetime.now().isoformat() + 'Z'
            if not self.validate_configuration(config_to_save):
                logger.error("❌ Cannot save invalid configuration")
                return False
            backup_path = self.config_path.with_suffix('.json.backup')
            if self.config_path.exists():
                import shutil
                shutil.copy2(self.config_path, backup_path)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            self.config = config_to_save
            logger.info(f"✅ Configuration saved to {self.config_path}")
            self.notify_observers()
            return True
        except Exception as e:
            logger.error(f"❌ Error saving configuration: {e}")
            return False

    def setup_file_watcher(self):
        """Setup file system watcher for hot-reload"""
        try:
            if self.file_observer:
                self.file_observer.stop()
            event_handler = ConfigurationFileHandler(self)
            self.file_observer = Observer()
            self.file_observer.schedule(
                event_handler,
                str(self.config_path.parent),
                recursive=False
            )
            self.file_observer.start()
            logger.info("🔍 Configuration file watcher started")
        except Exception as e:
            logger.error(f"❌ Error setting up file watcher: {e}")

    def reload_configuration(self):
        """Reload configuration from file and notify observers"""
        try:
            old_config = self.config.copy()
            new_config = self.load_configuration()
            if new_config != old_config:
                logger.info("🔄 Configuration changed, applying updates...")
                self.notify_observers()
                for callback in self.reload_callbacks:
                    try:
                        callback(old_config, new_config)
                    except Exception as e:
                        logger.error(f"❌ Error in reload callback: {e}")
        except Exception as e:
            logger.error(f"❌ Error reloading configuration: {e}")

    def add_reload_callback(self, callback: Callable[[Dict, Dict], None]):
        """Add callback to be executed when configuration is reloaded"""
        self.reload_callbacks.append(callback)

    def notify_observers(self):
        """Notify all observers of configuration changes"""
        for observer in self.observers:
            try:
                observer.on_config_changed(self.config)
            except Exception as e:
                logger.error(f"❌ Error notifying observer: {e}")

    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation"""
        try:
            keys = key_path.split('.')
            value = self.config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value
        except Exception:
            return default

    def set(self, key_path: str, value: Any) -> bool:
        """Set configuration value using dot notation"""
        try:
            keys = key_path.split('.')
            config = self.config
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            config[keys[-1]] = value
            return self.save_configuration()
        except Exception as e:
            logger.error(f"❌ Error setting configuration value: {e}")
            return False

    def get_trading_pairs(self) -> List[Dict]:
        """Get enabled trading pairs"""
        return [pair for pair in self.config['trading_pairs']['default_pairs'] if pair.get('enabled', True)]

    def get_websocket_channels(self) -> List[str]:
        """Get WebSocket channels for enabled trading pairs"""
        return [pair['channel'] for pair in self.get_trading_pairs()]

    def stop(self):
        """Stop the configuration manager and file watcher"""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            logger.info("🛑 Configuration file watcher stopped")

# Initialize global configuration manager
config_manager = ConfigurationManager()
