import importlib
import inspect
import os

from luserver.interfaces.plugin import ChatCommand

commands = []

with os.scandir(os.path.normpath(os.path.join(__file__, ".."))) as it:
	for entry in it:
		if entry.is_file():
			name, ext = os.path.splitext(entry.name)
			if ext == ".py" and name != "__init__":
				spec = importlib.util.spec_from_file_location("luserver.plugins.commands."+entry.name, entry.path)
				module = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(module)
				for name in dir(module):
					var = getattr(module, name)
					if not name.startswith("_") and inspect.isclass(var) and var is not ChatCommand and issubclass(var, ChatCommand):
						commands.append(var)

for command in commands:
	command()
