
class ServerModule:
	def __init__(self, server):
		self.server = server
		self.server.modules.append(self)

	def on_validated(self, address):
		"""Called when the session info has been received and validated. Modules should set up their listeners here so the server only acts when the connection is validated."""

	def on_disconnect_or_connection_lost(self, address):
		"""Called on disconnect or connection lost to an address."""

	def on_construction(self, obj):
		"""Called when an object is constructed."""

	def on_destruction(self, obj):
		"""Called when an object is destructed."""
