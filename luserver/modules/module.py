from ..world import server

class ServerModule:
	def __init__(self):
		server.modules.append(self)

	def on_validated(self, address):
		"""Called when the session info has been received and validated. Modules should set up their listeners here so the server only acts when the connection is validated."""
