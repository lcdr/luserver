
class ServerModule:
	def __init__(self, server):
		self.server = server
		self.server.modules.append(self)

	def on_validated(self, address):
		"""Called when the session info has been received and validated. modules should set up their listeners here so the server only acts when the connection is validated."""