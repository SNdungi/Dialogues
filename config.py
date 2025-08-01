import toml
import os

class _ConfigLoader:
	"""
	This class is the central point for loading ALL configuration and data
	from TOML files at the project root. It loads everything ONCE when the
	application starts.
	"""
	# --- CLASS VARIABLES TO HOLD THE LOADED DATA ---
	GlOBAL_CONFIG = {}

	def __init__(self):
		"""
		The constructor is run only once. It finds and loads all TOML files.
		"""
		# The project root is where this config.py file lives.
		project_root = os.path.dirname(os.path.abspath(__file__))
		
		# --- Define paths to ALL files this module will manage ---
		settings_path = os.path.join(project_root, 'config.toml')
		

		# --- Load Site Settings (config.toml) ---
		try:
			with open(settings_path, 'r', encoding='utf-8') as f:
					# Load the data directly into the class variable
					self.__class__.GlOBAL_CONFIG = toml.load(f)
			print(f"Site settings loaded successfully from: {settings_path}")
		except FileNotFoundError:
			print(f"WARNING: Site configuration file 'config.toml' not found.")
		except Exception as e:
			print(f"ERROR loading site settings: {e}")

config = _ConfigLoader()