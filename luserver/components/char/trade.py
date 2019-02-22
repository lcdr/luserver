from typing import cast, Optional

from bitstream import c_uint
from ...game_object import c_int64, c_uint64, E, EI, ES, EO, EP, GameObject, Mapping, ObjectID, Player, single
from ...game_object import c_uint as c_uint_
from ...world import server
from ...math.vector import Vector3
from ..inventory import InventoryType, LootType, Stack
from .subcomponent import CharSubcomponent

class TradeInviteResult:
	NotFound = 0
	InviteSent = 1
	OutOfRange = 2
	AlreadyTrading = 3
	GeneralError = 4

class Trade:
	def __init__(self) -> None:
		self.other_player: ObjectID = None
		self.accepted = False
		self.currency_offered = 0
		self.items_offered = {}

class CharTrade(CharSubcomponent):
	def __init__(self, player: Player) -> None:
		super().__init__(player)
		self.trade: Optional[Trade] = None

	def on_destruction(self) -> None:
		self.trade = None

	def on_client_trade_request(self, need_invite_pop_up:bool=False, invitee:Player=EP) -> None:
		# out of range error not implemented
		if (self.trade is not None and self.trade.other_player != invitee.object_id) \
		or (invitee.char.trade is not None and invitee.char.trade.other_player != self.object.object_id):
			result = TradeInviteResult.AlreadyTrading
		else:
			invitee.char.trade.server_trade_invite(need_invite_pop_up, requestor=self.object, name=self.object.name)
			invitee.char.trade = Trade()
			invitee.char.trade.other_player = self.object.object_id
			result = TradeInviteResult.InviteSent
		self.server_trade_initial_reply(invitee, result, invitee.name)

	@single
	def server_trade_invite(self, need_invite_pop_up:bool=False, requestor:GameObject=EO, name:str=ES) -> None:
		pass

	@single
	def server_trade_initial_reply(self, invitee:GameObject=EO, result_type:c_uint_=EI, name:str=ES) -> None:
		pass

	def on_client_trade_update(self, currency:c_uint64=E, items:Mapping[c_uint, c_int64, Stack]=E) -> None:
		self.trade.currency_offered = currency
		self.trade.items_offered = items
		trade_player = cast(Player, server.game_objects[self.trade.other_player])
		trade_player.char.trade.server_trade_update(currency=currency, items=items)

	@single
	def server_trade_update(self, about_to_perform:bool=False, currency:c_uint64=E, items:Mapping[c_uint, c_int64, Stack]=E) -> None:
		if about_to_perform:
			trade_player = cast(Player, server.game_objects[self.trade.other_player])
			if self.trade.currency_offered != 0:
				trade_player.char.set_currency(currency=trade_player.char.currency + self.trade.currency_offered, position=Vector3.zero, source_type=LootType.Trade, source_trade=self.object)
				self.object.char.set_currency(currency=self.object.char.currency - self.trade.currency_offered, position=Vector3.zero, source_type=LootType.Trade, source_trade=trade_player)
			for item in self.trade.items_offered.values():
				trade_player.inventory.add_item(item.lot, item.count, source_type=LootType.Trade)
				self.object.inventory.remove_item(InventoryType.Max, object_id=item.object_id, count=item.count)
			self.trade = None

	def client_trade_cancel(self) -> None:
		if self.trade is None:
			return
		trade_player = cast(Player, server.game_objects[self.trade.other_player])
		trade_player.char.trade.server_trade_cancel()
		self.trade = None

	def on_client_trade_accept(self, first:bool=False) -> None:
		self.trade.accepted = not first
		trade_player = cast(Player, server.game_objects[self.trade.other_player])
		trade_player.char.trade.server_trade_accept(first)

	@single
	def server_trade_cancel(self) -> None:
		self.trade = None

	@single
	def server_trade_accept(self, first:bool=False) -> None:
		if not first:
			if self.trade.accepted:
				trade_player = cast(Player, server.game_objects[self.trade.other_player])
				trade_player.char.trade.server_trade_update(True, 0, {})
				self.server_trade_update(True, 0, {})
