import os
from configparser import ConfigParser

class ConfigReader:
    """
    A utility class to read properties from config.properties file.
    """
    _config = None

    @classmethod
    def _get_config(cls):
        if cls._config is None:
            cls._config = ConfigParser()
            # Since config.properties is not a standard INI file (it lacks sections),
            # we can prepend a dummy section or use a different approach.
            # However, for a simple key=value file, we can just read it.
            # Let's add a dummy section [DEFAULT] to make it compatible with ConfigParser
            # if it doesn't have one.
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.properties')
            
            with open(config_path, 'r') as f:
                content = '[DEFAULT]\n' + f.read()
            
            cls._config.read_string(content)
        return cls._config

    @classmethod
    def get_property(cls, key, default=None):
        """
        Get a property value by key.
        """
        config = cls._get_config()
        return config.get('DEFAULT', key, fallback=default)

    @classmethod
    def get_bool_property(cls, key, default=False):
        """Get a boolean property by key using strict text normalization."""
        raw = cls.get_property(key, None)
        if raw is None:
            return default

        normalized = str(raw).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default

    @classmethod
    def get_uv_path(cls):
        """
        Dynamically resolve the UV path within the virtual environment.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if os.name == 'nt':
            path = os.path.join(project_root, ".venv", "Scripts", "uv.exe")
        else:
            path = os.path.join(project_root, ".venv", "bin", "uv")
        
        return path if os.path.exists(path) else cls.get_property("UV_PATH")

    @classmethod
    def get_site_packages_path(cls):
        """
        Dynamically resolve the site-packages path within the virtual environment.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if os.name == 'nt':
            path = os.path.join(project_root, ".venv", "Lib", "site-packages")
        else:
            # Unix-like systems have pythonX.X/site-packages
            lib_dir = os.path.join(project_root, ".venv", "lib")
            if os.path.exists(lib_dir):
                for item in os.listdir(lib_dir):
                    if item.startswith("python"):
                        path = os.path.join(lib_dir, item, "site-packages")
                        if os.path.exists(path):
                            return path
            path = cls.get_property("SITE_PACKAGES_PATH")
            
        return path if os.path.exists(path) else cls.get_property("SITE_PACKAGES_PATH")

    @classmethod
    def load_to_environ(cls, keys=None):
        """
        Load properties into os.environ.
        If keys is None, loads all properties.
        """
        config = cls._get_config()
        items = config.items('DEFAULT')
        for key, value in items:
            if keys is None or key.upper() in [k.upper() for k in keys]:
                os.environ[key.upper()] = value
