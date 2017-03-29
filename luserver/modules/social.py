import persistent.wref

from ..bitstream import c_bool, c_int64, c_ubyte, c_uint, c_uint64, c_ushort, WriteStream
from ..messages import SocialMsg, WorldClientMsg
from ..world import server

class AddFriendReturnCode:
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
	def __init__(self):
		server.social = self
		server.register_handler(SocialMsg.GetFriendsList, self.on_get_friends_list)
		server.register_handler(SocialMsg.AddFriendRequest, self.on_add_friend_request)
		server.register_handler(SocialMsg.AddFriendResponse, self.on_add_friend_response)
		server.register_handler(SocialMsg.RemoveFriend, self.on_remove_friend)
		server.register_handler(SocialMsg.TeamInvite, self.on_team_invite)
		server.register_handler(SocialMsg.TeamInviteResponse, self.on_team_invite_response)

	def on_get_friends_list(self, data, address):
		assert data.read(c_uint64) == 0 # seems to always be 0?

		friends = server.accounts[address].characters.selected().char.friends

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
		server.send(friends_list, address)

	def on_add_friend_request(self, request, address):
		assert request.read(c_int64) == 0
		requested_friend_name = request.read(str, allocated_length=33)
		is_best_friend_request = request.read(c_bool)

		try:
			requested_friend = server.find_player_by_name(requested_friend_name)
			# relay request to friend
			relayed_request = WriteStream()
			relayed_request.write_header(WorldClientMsg.AddFriendRequest)
			relayed_request.write(server.accounts[address].characters.selected().name, allocated_length=33)
			relayed_request.write(c_bool(is_best_friend_request))
			server.send(relayed_request, requested_friend.char.address)
		except KeyError:
			# friend cannot be found
			self.send_add_friend_response(AddFriendReturnCode.Failure, address, requested_name=requested_friend_name)

	def send_add_friend_response(self, return_code, address, friend=None, requested_name=None):
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
		server.send(response, address)

	def on_add_friend_response(self, response, address):
		assert response.read(c_int64) == 0
		request_declined = response.read(c_bool)
		requester_name = response.read(str, allocated_length=33)

		# should anything be sent if the responder declines?
		if not request_declined:
			responder = server.accounts[address].characters.selected()
			try:
				requester = server.find_player_by_name(requester_name)
				players = requester, responder
				for player1, player2 in (players, reversed(players)):
					player1.char.friends.append(persistent.wref.WeakRef(player2))
					self.send_add_friend_response(AddFriendReturnCode.Success, player1.char.address, friend=player2)
			except KeyError:
				self.send_add_friend_response(AddFriendReturnCode.Failure, player1.char.address, requested_name=requester_name)

	def on_remove_friend(self, request, address):
		assert request.read(c_int64) == 0
		requested_friend_name = request.read(str, allocated_length=33)

		requester = server.accounts[address].characters.selected()
		requested_friend_ref = [i for i in requester.char.friends if i().name == requested_friend_name][0]
		requester_ref = [i for i in requested_friend_ref().char.friends if i().name == requester.name][0]

		players = requester_ref, requested_friend_ref

		for player1_ref, player2_ref in (players, reversed(players)):
			player1_ref().char.friends.remove(player2_ref)

			remove_message = WriteStream()
			remove_message.write_header(WorldClientMsg.RemoveFriendResponse)
			remove_message.write(c_bool(True)) # Successful
			remove_message.write(player2_ref().name, allocated_length=33)
			server.send(remove_message, player1_ref().char.address)

	def on_team_invite(self, invite, address):
		assert invite.read(c_int64) == 0
		invitee_name = invite.read(str, allocated_length=33)

		sender = server.accounts[address].characters.selected()
		invitee = server.find_player_by_name(invitee_name)

		relayed_invite = WriteStream()
		relayed_invite.write_header(WorldClientMsg.TeamInvite)
		relayed_invite.write(sender.name, allocated_length=33)
		relayed_invite.write(c_int64(sender.object_id))
		server.send(relayed_invite, invitee.char.address)
		# todo: error cases and response

	def on_team_invite_response(self, response, address):
		assert response.read(c_int64) == 0
		is_denied = response.read(c_bool)
		inviter_object_id = response.read(c_int64)

		print("TODO: actually act")
