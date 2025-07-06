from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from plugins.astrology_chat.models import ChatSession, ChatMessage, KnowledgeCategory, KnowledgeDocument
from plugins.astrology_chat.services.chat_service import ChatService
from django.urls import reverse
from unittest.mock import patch

User = get_user_model()

class AstrologyChatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.premium_user = User.objects.create_user(
            username='premium', email='premium@example.com', password='testpass', is_premium=True
        )
        self.regular_user = User.objects.create_user(
            username='regular', email='regular@example.com', password='testpass', is_premium=False
        )
        self.category = KnowledgeCategory.objects.create(name='Test Category')
        self.knowledge_doc = KnowledgeDocument.objects.create(
            title='Test Doc',
            description='A test document',
            category=self.category,
            content='Astrology is the study of the movements and relative positions of celestial bodies.',
            is_processed=True,
            is_active=True
        )

    def test_premium_user_can_create_chat_session(self):
        self.client.login(username='premium', password='testpass')
        response = self.client.get(reverse('new_chat_session'))
        self.assertEqual(response.status_code, 302)  # Should redirect to session page
        session = ChatSession.objects.filter(user=self.premium_user).first()
        self.assertIsNotNone(session)

    def test_regular_user_cannot_access_chat(self):
        self.client.login(username='regular', password='testpass')
        response = self.client.get(reverse('astrology_chat_dashboard'))
        self.assertRedirects(response, '/payments/pricing/')

    @patch('plugins.astrology_chat.services.chat_service.generate_interpretation')
    def test_send_message_and_receive_ai_response(self, mock_generate):
        mock_generate.return_value = 'This is an AI response.'
        self.client.login(username='premium', password='testpass')
        session = ChatSession.objects.create(user=self.premium_user, title='Test Session')
        url = reverse('send_chat_message', args=[session.id])
        response = self.client.post(url, {'content': 'What is my sun sign?'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('ai_message', data)
        self.assertEqual(data['ai_message']['content'], 'This is an AI response.')
        # Check that both user and AI messages are saved
        self.assertEqual(ChatMessage.objects.filter(session=session).count(), 2)

    def test_knowledge_base_search(self):
        self.client.login(username='premium', password='testpass')
        url = reverse('api_knowledge_search') + '?q=celestial'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertGreaterEqual(len(data['results']), 1)
        self.assertIn('Astrology is the study', data['results'][0]['content'])

    def test_access_control_for_knowledge_base(self):
        self.client.login(username='regular', password='testpass')
        url = reverse('knowledge_base')
        response = self.client.get(url)
        self.assertRedirects(response, '/payments/pricing/') 