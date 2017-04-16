
class ChatCommand:
	def __init__(self, chat, *args, **kwargs):
		self.chat = chat
		self.command = chat.commands.add_parser(*args, **kwargs)
		self.command.set_defaults(func=self.run)

	def run(self, args, sender):
		raise NotImplementedError

def toggle_bool(str_):
	str_ = str_.lower()
	if str_ == "toggle":
		return None
	return normal_bool(str_)

def normal_bool(str_):
	str_ = str_.lower()
	if str_ in ("true", "on"):
		return True
	if str_ in ("false", "off"):
		return False
	raise ValueError
