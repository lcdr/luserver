
class ChatCommand:
	def __init__(self, chat, *args, **kwargs):
		self.chat = chat
		self.command = chat.commands.add_parser(*args, **kwargs)
		self.command.set_defaults(func=self.run)
