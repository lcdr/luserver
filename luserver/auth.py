from typing import Dict, TYPE_CHECKING

from persistent import Persistent
from persistent.mapping import PersistentMapping
if TYPE_CHECKING:
	from .game_object import Player

from pyraknet.transports.abc import Connection

class Account(Persistent):
	def __init__(self, username: str, password: str):
		self.username = username
		self.password = hash.hash(password)
		self.password_state = PasswordState.Set
		self.session_key = ""
		#self.address = address
		self.muted_until = 0
		self.banned_until = 0
		self.gm_level = GMLevel.Nothing
		self.characters: Dict[str, "Player"] = PersistentMapping()
		self.selected_char_name = ""

	def selected_char(self) -> "Player":
		return self.characters[self.selected_char_name]

	def set_password(self, password: str) -> None:
		self.password = hash.hash(password)

class GMLevel:
	Nothing = 0
	Mod = 50
	Admin = 100

class PasswordState:
	Temp = 0
	AcceptNew = 1
	Set = 2
