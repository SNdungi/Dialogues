import toml
import os
import pprint

class _ConfigLoader:
    """Load ALL configuration from TOML files once at startup."""

    GLOBAL_CONFIG = {}

    def __init__(self):
        project_root = os.path.dirname(os.path.abspath(__file__))
        settings_path = os.path.join(project_root, 'config.toml')

        try:
            # ✅ Pass the filename, not file object, not dict
            self.__class__.GLOBAL_CONFIG = toml.load(settings_path)
            print(f"Site settings loaded successfully from: {settings_path}")
        except FileNotFoundError:
            print("WARNING: Site configuration file 'config.toml' not found.")
        except Exception as e:
            print(f"ERROR loading site settings: {e}")

config = _ConfigLoader()


