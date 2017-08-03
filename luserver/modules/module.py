from ..world import server

class ServerModule:
	def __init__(self):
		server.modules.append(self)
