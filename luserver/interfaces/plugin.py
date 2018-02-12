from argparse import ArgumentTypeError
from typing import Any, List, Optional

from ..auth import GMLevel
from ..game_object import GameObject, Player
from ..world import server

class ChatCommand:
	def __init__(self, *args: Any, **kwargs: Any):
		self.command = server.chat.commands.add_parser(*args, **kwargs)
		self.command.set_defaults(func=self.run)
		self.command.set_defaults(perm=GMLevel.Admin)

	def run(self, args: Any, sender: GameObject) -> None:
		raise NotImplementedError

def toggle_bool(str_: str) -> Optional[bool]:
	str_ = str_.lower()
	if str_ == "toggle":
		return None
	return normal_bool(str_)

def normal_bool(str_: str) -> bool:
	str_ = str_.lower()
	if str_ in ("true", "on"):
		return True
	if str_ in ("false", "off"):
		return False
	raise ValueError

def object_selector(str_: str) -> List[GameObject]:
	selected = []
	for obj in server.game_objects.values():
		if str_.startswith("!"):
			if obj.name == str_[1:]:
				selected.append(obj)
	return selected

def instance_obj(name: str) -> GameObject:
	if not name.startswith("!"):
		return instance_player(name)
	else:
		name = name[1:]
	name = name.lower()
	for obj in server.game_objects.values():
		if obj.name.lower().startswith(name):
			return obj
	raise ArgumentTypeError("Object not found in instance")

def instance_player(name: str) -> Player:
	name = name.lower()
	for obj in server.game_objects.values():
		if isinstance(obj, Player) and obj.name.lower().startswith(name):
			return obj
	raise ArgumentTypeError("Player not found in instance")
