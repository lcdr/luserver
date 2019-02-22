from bitstream import c_uint
from luserver.tests.test_world import SessionWorldTest
from luserver.bitstream import WriteStream
from luserver.messages import WorldClientMsg, WorldServerMsg
from luserver.modules.mail import MailID
from luserver.components.inventory import Stack

class MailTest(SessionWorldTest):
	def set_up_db(self):
		super().set_up_db()
		self.db.components_registry[4084] = [(2, 3506), (11, 1147)]
		self.db.item_component = {1147: (100, 15, 1, ())}

	def test_send_mail(self):
		attachment = Stack(self.db, self.server.new_object_id(), 4084)
		self.server.mail.send_mail("sender", "subject", "body", self.player, attachment)
		self.assertEqual(len(self.player.char.mails), 1)
		mail = self.player.char.mails[0]
		self.assertEqual(mail.sender, "sender")
		self.assertEqual(mail.subject, "subject")
		self.assertEqual(mail.body, "body")
		self.assertIs(mail.attachment, attachment)

	def test_mail_notification(self):
		self.server.mail.send_mail("sender", "subject", "body", self.player)
		request = WriteStream()
		request.write_header(WorldServerMsg.Mail)
		request.write(c_uint(MailID.MailNotificationRequest))
		self.server._on_lu_packet(bytes(request), self.ADDRESS)
		response = WriteStream()
		response.write_header(WorldClientMsg.Mail)
		response.write(c_uint(MailID.MailNotification))
		response.write(bytes(4+32))
		response.write(c_uint(1))
		response.write(bytes(4))
		self.assert_sent(response)
