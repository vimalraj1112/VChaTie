from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Profile, Conversation, Message


class UserRegistrationTests(TestCase):
    def test_register_creates_user(self):
        """A valid registration should create a real User in the database."""
        response = self.client.post(reverse('register'), {
            'username': 'testuser1',
            'password': 'testpass123'
        })
        self.assertTrue(User.objects.filter(username='testuser1').exists())

    def test_register_rejects_short_password(self):
        """Passwords under 6 characters should be rejected."""
        response = self.client.post(reverse('register'), {
            'username': 'testuser2',
            'password': '123'
        })
        self.assertFalse(User.objects.filter(username='testuser2').exists())

    def test_register_rejects_duplicate_username(self):
        """Two users can't have the same username."""
        User.objects.create_user(username='raj', password='pass123456')
        response = self.client.post(reverse('register'), {
            'username': 'raj',
            'password': 'anotherpass123'
        })
        self.assertEqual(User.objects.filter(username='raj').count(), 1)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='raj', password='mypassword123')

    def test_login_with_correct_credentials(self):
        response = self.client.post(reverse('login'), {
            'username': 'raj',
            'password': 'mypassword123'
        })
        self.assertRedirects(response, reverse('inbox'))

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(reverse('login'), {
            'username': 'raj',
            'password': 'wrongpassword'
        })
        self.assertContains(response, 'Invalid Credentials')

    def test_inbox_requires_login(self):
        """An anonymous user should be redirected away from inbox."""
        response = self.client.get(reverse('inbox'))
        self.assertNotEqual(response.status_code, 200)


class ConversationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='raj', password='pass123456')
        self.user2 = User.objects.create_user(username='vimal', password='pass123456')
        self.conversation = Conversation.objects.create(is_group=False)
        self.conversation.participants.add(self.user1, self.user2)

    def test_conversation_has_two_participants(self):
        self.assertEqual(self.conversation.participants.count(), 2)

    def test_message_is_saved_correctly(self):
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            text='Hello vimal!'
        )
        self.assertEqual(self.conversation.message.count(), 1)
        self.assertEqual(message.sender.username, 'raj')

    def test_non_participant_cannot_access_room(self):
        """A user who isn't part of the conversation shouldn't be able to send messages via the API."""
        outsider = User.objects.create_user(username='akash', password='pass123456')
        self.client.login(username='akash', password='pass123456')

        response = self.client.post(
            reverse('api_send_message', args=[self.conversation.id]),
            {'text': 'I should not be able to send this'}
        )
        self.assertEqual(response.status_code, 403)


class DeleteMessageTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='raj', password='pass123456')
        self.user2 = User.objects.create_user(username='vimal', password='pass123456')
        self.conversation = Conversation.objects.create(is_group=False)
        self.conversation.participants.add(self.user1, self.user2)
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            text='This will be deleted'
        )

    def test_sender_can_delete_own_message(self):
        self.client.login(username='raj', password='pass123456')
        self.client.post(reverse('delete_message', args=[self.message.id]))
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_deleted)
        self.assertEqual(self.message.text, "This message was deleted")

    def test_other_user_cannot_delete_someone_elses_message(self):
        """Security check: vimal should NOT be able to delete raj's message."""
        self.client.login(username='vimal', password='pass123456')
        self.client.post(reverse('delete_message', args=[self.message.id]))
        self.message.refresh_from_db()
        self.assertFalse(self.message.is_deleted)
        self.assertEqual(self.message.text, 'This will be deleted')