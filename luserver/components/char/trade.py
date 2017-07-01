from ...math.vector import Vector3
from ...bitstream import c_int64, c_uint, c_uint64
from ...game_object import GameObject
from ...messages import single
from ...world import server
from ..inventory import InventoryType, LootType, Stack

class TradeInviteResult:
	NotFound = 0
	InviteSent = 1
	OutOfRange = 2
	AlreadyTrading = 3
	GeneralError = 4

class Trade:
	def __init__(self):
		self.other_player = None
		self.accepted = False
		self.currency_offered = 0
		self.items_offered = {}

class CharTrade:
	def __init__(self):
		self.trade = None

	def on_destruction(self):
		self.trade = None

	def client_trade_request(self, need_invite_pop_up:bool=False, invitee:GameObject=None):
		# out of range error not implemented
		if (self.trade is not None and self.trade.other_player != invitee.object_id) \
		or (invitee.char.trade is not None and invitee.char.trade.other_player != self.object.object_id):
			result = TradeInviteResult.AlreadyTrading
		else:
			invitee.char.server_trade_invite(need_invite_pop_up, requestor=self.object, name=self.object.name)
			invitee.char.trade = Trade()
			invitee.char.trade.other_player = self.object.object_id
			result = TradeInviteResult.InviteSent
		self.server_trade_initial_reply(invitee, result, invitee.name)

	@single
	def server_trade_invite(self, need_invite_pop_up:bool=False, requestor:GameObject=None, name:str=None):
		pass

	@single
	def server_trade_initial_reply(self, invitee:GameObject=None, result_type:c_uint=None, name:str=None):
		pass

	def client_trade_update(self, currency:c_uint64=None, items:(c_uint, c_int64, Stack)=None):
		self.trade.currency_offered = currency
		self.trade.items_offered = items
		trade_player = server.game_objects[self.trade.other_player]
		trade_player.char.server_trade_update(currency=currency, items=items)

	@single
	def server_trade_update(self, about_to_perform:bool=False, currency:c_uint64=None, items:(c_uint, c_int64, Stack)=None):
		if about_to_perform:
			trade_player = server.game_objects[self.trade.other_player]
			if self.trade.currency_offered != 0:
				trade_player.char.set_currency(currency=trade_player.char.currency + self.trade.currency_offered, position=Vector3.zero, source_type=LootType.Trade, source_trade_id=self.object)
				self.set_currency(currency=self.currency - self.trade.currency_offered, position=Vector3.zero, source_type=LootType.Trade, source_trade_id=trade_player)
			for item in self.trade.items_offered.values():
				trade_player.inventory.add_item_to_inventory(item.lot, item.amount, source_type=LootType.Trade)
				self.object.inventory.remove_item_from_inv(InventoryType.Max, object_id=item.object_id, amount=item.amount)
			self.trade = None

	def client_trade_cancel(self):
		if self.trade is None:
			return
		trade_player = server.game_objects[self.trade.other_player]
		trade_player.char.server_trade_cancel()
		self.trade = None

	def client_trade_accept(self, first:bool=False):
		self.trade.accepted = not first
		trade_player = server.game_objects[self.trade.other_player]
		trade_player.char.server_trade_accept(first)

	@single
	def server_trade_cancel(self):
		self.trade = None

	@single
	def server_trade_accept(self, first:bool=False):
		if not first:
			if self.trade.accepted:
				trade_player = server.game_objects[self.trade.other_player]
				trade_player.char.server_trade_update(True, 0, {})
				self.server_trade_update(True, 0, {})
