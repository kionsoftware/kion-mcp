"""Configuration management for Kion MCP Server."""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Optional, Tuple
from ..exceptions import ConfigurationError
from ..utils.dxt import is_dxt_mode


# Placeholder values for config template
PLACEHOLDER_VALUES = {
    'server_base_url': 'https://your-kion-instance.com',
    'bearer_token': 'your_bearer_token_here'
}


class KionConfig:
    """Configuration class for Kion MCP Server."""
    
    def __init__(self):
        self.server_base_url: Optional[str] = None
        self.bearer_token: Optional[str] = None
        self.auth_script_path: Optional[str] = None
        self._config_path: Optional[str] = None
        self._loaded_from_env: bool = False
    
    @classmethod
    def load(cls) -> 'KionConfig':
        """Load configuration from environment or file with priority."""
        config = cls()
        
        # Priority 1: Environment variables (DXT mode)
        if config._load_from_environment():
            return config
            
        # Priority 2: Config file (standalone mode)  
        config._load_from_file()
        return config
    
    def reload(self) -> None:
        """Reload configuration based on original source."""
        if self._loaded_from_env:
            self._load_from_environment()
        else:
            self._load_from_file()
    
    def _load_from_environment(self) -> bool:
        """Load configuration from environment variables.
        
        Returns:
            bool: True if environment variables found and loaded, False otherwise.
        """
        server_url = os.getenv('KION_SERVER_URL')
        bearer_token = os.getenv('KION_BEARER_TOKEN')
        
        # Only proceed if we have at least server URL from environment
        if not server_url:
            return False
        
        try:
            self.server_base_url = self._process_server_url(server_url)
            self.bearer_token = bearer_token
            self.auth_script_path = None  #Auth script not used in DXT mode
            self._loaded_from_env = True
            
            logging.info("Configuration loaded from environment variables (DXT mode)")
            return True
            
        except Exception as e:
            logging.error(f"Error processing environment configuration: {e}")
            return False
    
    def _find_valid_config_file(self) -> Optional[str]:
        """Find the best available config file, preferring valid configs."""
        config_filename = 'kion_mcp_config.yaml'
        script_dir_path = (Path(__file__).parent.parent.parent.parent / config_filename).resolve()
        home_dir_path = (Path.home() / config_filename).resolve()
        
        # Check script directory first
        if script_dir_path.exists():
            script_data, script_valid = self._load_and_validate_config(str(script_dir_path))
            if script_valid:
                return str(script_dir_path)
        
        # Check home directory for fallback
        if home_dir_path.exists():
            home_data, home_valid = self._load_and_validate_config(str(home_dir_path)) 
            if home_valid:
                return str(home_dir_path)
        
        # Return script path if it exists, or None
        return str(script_dir_path) if script_dir_path.exists() else None
    
    def _load_from_file(self) -> None:
        """Load configuration from YAML file."""
        config_path = self._find_valid_config_file()
        if not config_path:
            raise ConfigurationError("Configuration file not found")
        
        self._config_path = Path(config_path)
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            
            # Store raw values first for placeholder detection
            raw_server_url = config_data.get('server_base_url')
            self.bearer_token = config_data.get('bearer_token')
            self.auth_script_path = config_data.get('auth_script_path')
            
            # Only process URL if it's not a placeholder
            if raw_server_url and not self._is_placeholder_value('server_base_url', raw_server_url):
                self.server_base_url = self._process_server_url(raw_server_url)
            else:
                self.server_base_url = raw_server_url
            
            logging.info(f"Configuration loaded from: {Path(config_path).resolve()}")
            
        except Exception as e:
            raise ConfigurationError(f"Error reading config file: {e}")
    
    def _process_server_url(self, url: Optional[str]) -> Optional[str]:
        """Process the server URL to ensure it points to the correct API endpoint."""
        if not url:
            return url
        
        # Remove trailing slash if present
        url = url.rstrip('/')
        
        # Check if it's localhost
        if 'localhost' in url.lower():
            # For localhost, ensure we're using port 8081 and no path
            if '://' in url:
                protocol = url.split('://')[0]
                return f"{protocol}://localhost:8081"
            else:
                return "http://localhost:8081"
        
        # Handle real urls to ensure they have a protocol and /api path
        if '://' in url:
            # URL has protocol
            parts = url.split('/', 3)  # Split into protocol, empty, domain, path
            if len(parts) >= 3:
                # Reconstruct URL with just protocol and domain, then add /api
                base_url = f"{parts[0]}//{parts[2]}"
                return f"{base_url}/api"
        else:
            # No protocol - extract just the domain part before any path
            domain = url.split('/')[0]
            return f"https://{domain}/api"
    
    def save(self) -> None:
        """Save configuration to file."""
        if not self._config_path:
            # Create config in script directory if no path exists
            self._config_path = Path(__file__).parent.parent.parent.parent / 'kion_mcp_config.yaml'
        
        config_data = {}
        if self.server_base_url:
            config_data['server_base_url'] = self.server_base_url
        if self.bearer_token:
            config_data['bearer_token'] = self.bearer_token
        if self.auth_script_path:
            config_data['auth_script_path'] = self.auth_script_path
        
        try:
            with open(self._config_path, 'w') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False)
            logging.info(f"Configuration saved to: {self._config_path.resolve()}")
        except Exception as e:
            raise ConfigurationError(f"Error saving config file: {e}")
    
    def _is_placeholder_value(self, key: str, value: str) -> bool:
        """Check if a value is a placeholder."""
        if not value:
            return True
        
        stripped_value = value.strip()
        
        # Check against predefined placeholder values
        if stripped_value == PLACEHOLDER_VALUES.get(key, ''):
            return True
        
        # Check if value is wrapped in angle brackets (e.g., "<your-value-here>")
        if stripped_value.startswith('<') and stripped_value.endswith('>'):
            return True
        
        return False
    
    def _load_and_validate_config(self, config_path: str) -> Tuple[dict, bool]:
        """Load config from path and validate if it has valid server URL."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            return config_data, self._has_valid_server_url(config_data)
        except Exception as e:
            logging.warning(f"Failed to load config from {config_path}: {e}")
            return {}, False
    
    def _has_valid_server_url(self, config_data: dict) -> bool:
        """Check if config has valid server URL (only requirement for full mode)."""
        server_url = config_data.get('server_base_url')
        return server_url and not self._is_placeholder_value('server_base_url', server_url)
    
    def needs_configuration(self) -> bool:
        """Check if configuration needs setup (only checks server URL)."""
        return not self.has_real_server_url()
    
    def is_script_auth_mode(self) -> bool:
        """Check if using script-based authentication."""
        return self.auth_script_path is not None
    
    def has_real_bearer(self) -> bool:
        """Check if we have a real bearer token (not a placeholder)."""
        return self.bearer_token and not self._is_placeholder_value('bearer_token', self.bearer_token)
    
    def has_real_server_url(self) -> bool:
        """Check if we have a real server URL (not a placeholder)."""
        return self.server_base_url and not self._is_placeholder_value('server_base_url', self.server_base_url)
    
    def has_auth_script(self) -> bool:
        """Check if we have a configured auth script."""
        return self.auth_script_path and self.auth_script_path.strip()
    
    def create_placeholder_config(self) -> str:
        """Create a placeholder config file in the script directory."""
        config_path = Path(__file__).parent.parent.parent.parent / 'kion_mcp_config.yaml'
        
        config_data = {
            'server_base_url': PLACEHOLDER_VALUES['server_base_url'],
            'bearer_token': PLACEHOLDER_VALUES['bearer_token']
        }
        
        try:
            with open(config_path, 'w') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False)
            logging.info(f"Placeholder configuration created at: {config_path.resolve()}")
            self._config_path = config_path
            return str(config_path.resolve())
        except Exception as e:
            raise ConfigurationError(f"Error creating placeholder config file: {e}")


def save_app_config_cache(app_config: dict) -> None:
    """Save app config to cache file."""
    try:
        cache_path = _get_cache_path()
        with open(cache_path, 'w') as f:
            json.dump(app_config, f, indent=2)
        logging.info(f"App config cached to: {Path(cache_path).resolve()}")
    except Exception as e:
        logging.warning(f"Failed to save app config cache: {e}")


def load_app_config_cache() -> Optional[dict]:
    """Load app config from cache file."""
    try:
        cache_path = _get_cache_path()
        if not os.path.exists(cache_path):
            return None
        
        with open(cache_path, 'r') as f:
            app_config = json.load(f)
        
        logging.info(f"App config loaded from cache: {Path(cache_path).resolve()}")
        return app_config
    except Exception as e:
        logging.warning(f"Failed to load app config cache: {e}")
        return None


def _get_cache_path() -> str:
    """Get the path for the app config cache file."""
    # Place cache file in same directory as the main config file
    cache_path = Path(__file__).parent.parent.parent.parent / 'kion_mcp_app_config_cache.json'
    return str(cache_path.resolve())