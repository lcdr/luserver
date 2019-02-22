import persistent.wref

from bitstream import c_bool, c_int64, c_ubyte, c_uint, c_uint64, c_ushort, ReadStream
from pyraknet.transports.abc import Connection
from ..bitstream import WriteStream
from ..game_object import Player
from ..messages import SocialMsg, WorldClientMsg
from ..world import server

class _AddFriendReturnCode:
	Success = 0
	IsAlreadyFriend = 1
	InvalidName = 2
	Failure = 3
	RequesterFriendsListFull = 4
	RequesteeFriendsListFull = 5

class FriendUpdateType:
	Logout = 0
	Login = 1
	WorldChange = 2

class SocialHandling:
	def __init__(self) -> None:
		server._dispatcher.add_listener(SocialMsg.GetFriendsList, self._on_get_friends_list)
		server._dispatcher.add_listener(SocialMsg.AddFriendRequest, self._on_add_friend_request)
		server._dispatcher.add_listener(SocialMsg.AddFriendResponse, self._on_add_friend_response)
		server._dispatcher.add_listener(SocialMsg.RemoveFriend, self._on_remove_friend)
		server._dispatcher.add_listener(SocialMsg.TeamInvite, self._on_team_invite)
		server._dispatcher.add_listener(SocialMsg.TeamInviteResponse, self._on_team_invite_response)

	def _on_get_friends_list(self, data: ReadStream, conn: Connection) -> None:
		assert data.read(c_uint64) == 0 # seems to always be 0?

		friends = server.accounts[conn].selected_char().char.friends

		friends_list = WriteStream()
		friends_list.write_header(WorldClientMsg.FriendsList)
		friends_list.write(bytes(1)) # ???
		friends_list.write(bytes(2)) # length of packet - 1, does not seem to be required
		friends_list.write(c_ushort(len(friends)))
		for friend_ref in friends:
			friend = friend_ref()
			friends_list.write(c_bool(friend.char.online))
			friends_list.write(c_bool(False)) # is best friend
			friends_list.write(c_bool(False)) # is FTP
			friends_list.write(bytes(5)) # ???
			friends_list.write(c_ushort(friend.char.world[0]))
			friends_list.write(c_ushort(friend.char.world[1]))
			friends_list.write(c_uint(friend.char.world[2]))
			friends_list.write(c_int64(friend.object_id))
			friends_list.write(friend.name, allocated_length=33)
			friends_list.write(bytes(6)) # ???
		conn.send(friends_list)

	def _on_add_friend_request(self, request: ReadStream, conn: Connection) -> None:
		assert request.read(c_int64) == 0
		requested_friend_name = request.read(str, allocated_length=33)
		is_best_friend_request = request.read(c_bool)

		try:
			requested_friend = server.find_player_by_name(requested_friend_name)
			# relay request to friend
			relayed_request = WriteStream()
			relayed_request.write_header(WorldClientMsg.AddFriendRequest)
			relayed_request.write(server.accounts[conn].selected_char().name, allocated_length=33)
			relayed_request.write(c_bool(is_best_friend_request))
			requested_friend.char.data()["conn"].send(relayed_request)
		except KeyError:
			# friend cannot be found
			self._send_add_friend_response(_AddFriendReturnCode.Failure, conn, requested_name=requested_friend_name)

	def _send_add_friend_response(self, return_code: int, conn: Connection, friend: Player=None, requested_name: str=None) -> None:
		response = WriteStream()
		response.write_header(WorldClientMsg.AddFriendResponse)
		response.write(c_ubyte(return_code))
		if friend is not None:
			response.write(c_bool(friend.char.online))
			response.write(friend.name, allocated_length=33)
			response.write(c_int64(friend.object_id))
			response.write(c_ushort(friend.char.world[0]))
			response.write(c_ushort(friend.char.world[1]))
			response.write(c_uint(friend.char.world[2]))
		else:
			response.write(bytes(1))
			response.write(requested_name, allocated_length=33)
			response.write(bytes(16))

		response.write(c_bool(False)) # is best friend (not implemented)
		response.write(c_bool(False)) # is FTP
		conn.send(response)

	def _on_add_friend_response(self, response: ReadStream, conn: Connection) -> None:
		assert response.read(c_int64) == 0
		request_declined = response.read(c_bool)
		requester_name = response.read(str, allocated_length=33)

		# should anything be sent if the responder declines?
		if not request_declined:
			responder = server.accounts[conn].selected_char()
			try:
				requester = server.find_player_by_name(requester_name)
				players = requester, responder
				for player1, player2 in (players, reversed(players)):
					player1.char.friends.append(persistent.wref.WeakRef(player2))
					self._send_add_friend_response(_AddFriendReturnCode.Success, player1.char.data()["conn"], friend=player2)
			except KeyError:
				self._send_add_friend_response(_AddFriendReturnCode.Failure, player1.char.data()["conn"], requested_name=requester_name)

	def _on_remove_friend(self, request: ReadStream, conn: Connection) -> None:
		assert request.read(c_int64) == 0
		requested_friend_name = request.read(str, allocated_length=33)

		requester = server.accounts[conn].selected_char()
		requested_friend_ref = [i for i in requester.char.friends if i().name == requested_friend_name][0]
		requester_ref = [i for i in requested_friend_ref().char.friends if i().name == requester.name][0]

		players = requester_ref, requested_friend_ref

		for player1_ref, player2_ref in (players, reversed(players)):
			player1_ref().char.friends.remove(player2_ref)

			remove_message = WriteStream()
			remove_message.write_header(WorldClientMsg.RemoveFriendResponse)
			remove_message.write(c_bool(True)) # Successful
			remove_message.write(player2_ref().name, allocated_length=33)
			player1_ref().char.data()["conn"].send(remove_message)

	def _on_team_invite(self, invite: ReadStream, conn: Connection) -> None:
		assert invite.read(c_int64) == 0
		invitee_name = invite.read(str, allocated_length=33)

		sender = server.accounts[conn].selected_char()
		invitee = server.find_player_by_name(invitee_name)

		relayed_invite = WriteStream()
		relayed_invite.write_header(WorldClientMsg.TeamInvite)
		relayed_invite.write(sender.name, allocated_length=33)
		relayed_invite.write(c_int64(sender.object_id))
		invitee.char.data()["conn"].send(relayed_invite)
		# todo: error cases and response

	def _on_team_invite_response(self, response: ReadStream, conn: Connection) -> None:
		assert response.read(c_int64) == 0
		is_denied = response.read(c_bool)
		inviter_object_id = response.read(c_int64)

		print("TODO: actually act")
