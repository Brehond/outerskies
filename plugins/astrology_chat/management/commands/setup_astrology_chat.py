from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from plugins.astrology_chat.models import KnowledgeCategory, ChatAnalytics
from plugins.astrology_chat.services.knowledge_service import KnowledgeService
import os
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Set up the Astrology Chat plugin with initial configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-categories',
            action='store_true',
            help='Create default knowledge base categories',
        )
        parser.add_argument(
            '--setup-demo-data',
            action='store_true',
            help='Create demo chat sessions and documents',
        )
        parser.add_argument(
            '--process-documents',
            action='store_true',
            help='Process all pending documents in the knowledge base',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old sessions and documents',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Setting up Astrology Chat Plugin...')
        )

        if options['create_categories']:
            self.create_default_categories()

        if options['setup_demo_data']:
            self.setup_demo_data()

        if options['process_documents']:
            self.process_documents()

        if options['cleanup']:
            self.cleanup_old_data()

        self.stdout.write(
            self.style.SUCCESS('✅ Astrology Chat Plugin setup complete!')
        )

    def create_default_categories(self):
        """Create default knowledge base categories"""
        self.stdout.write('Creating default knowledge base categories...')

        default_categories = [
            {
                'name': 'Planetary Meanings',
                'description': 'Core meanings and interpretations of planets',
                'color': '#FF6B6B',
                'order': 1
            },
            {
                'name': 'House Interpretations',
                'description': 'Astrological houses and their significance',
                'color': '#4ECDC4',
                'order': 2
            },
            {
                'name': 'Aspect Analysis',
                'description': 'Planetary aspects and their interpretations',
                'color': '#45B7D1',
                'order': 3
            },
            {
                'name': 'Zodiac Signs',
                'description': 'Characteristics and traits of zodiac signs',
                'color': '#96CEB4',
                'order': 4
            },
            {
                'name': 'Traditional Astrology',
                'description': 'Classical and traditional astrological techniques',
                'color': '#FFEAA7',
                'order': 5
            },
            {
                'name': 'Modern Astrology',
                'description': 'Contemporary astrological approaches',
                'color': '#DDA0DD',
                'order': 6
            },
            {
                'name': 'Techniques & Methods',
                'description': 'Astrological calculation methods and techniques',
                'color': '#98D8C8',
                'order': 7
            },
            {
                'name': 'Transits & Progressions',
                'description': 'Transit and progression interpretations',
                'color': '#F7DC6F',
                'order': 8
            },
            {
                'name': 'Synastry & Compatibility',
                'description': 'Relationship astrology and compatibility',
                'color': '#BB8FCE',
                'order': 9
            },
            {
                'name': 'Electional Astrology',
                'description': 'Choosing auspicious times for events',
                'color': '#85C1E9',
                'order': 10
            }
        ]

        created_count = 0
        for category_data in default_categories:
            category, created = KnowledgeCategory.objects.get_or_create(
                name=category_data['name'],
                defaults=category_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Created category: {category.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} new categories')
        )

    def setup_demo_data(self):
        """Create demo data for testing"""
        self.stdout.write('Setting up demo data...')

        # Create demo user if needed
        demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_premium': True
            }
        )

        if created:
            self.stdout.write('  ✓ Created demo user')

        # Create demo chat sessions
        from plugins.astrology_chat.models import ChatSession, ChatMessage

        demo_sessions = [
            {
                'title': 'Understanding My Sun Sign',
                'context_notes': 'Exploring the meaning of Sun in Leo and its impact on personality',
                'messages': [
                    {
                        'content': 'Can you explain what having Sun in Leo means for my personality?',
                        'is_ai': False
                    },
                    {
                        'content': 'Having Sun in Leo indicates a natural leadership quality, creativity, and a warm, generous personality. Leos are known for their confidence, dramatic flair, and ability to inspire others. Your Sun sign represents your core identity and ego expression.',
                        'is_ai': True,
                        'tokens_used': 45
                    }
                ]
            },
            {
                'title': 'Moon Sign Analysis',
                'context_notes': 'Deep dive into emotional nature and inner self',
                'messages': [
                    {
                        'content': 'What does my Moon sign tell me about my emotional nature?',
                        'is_ai': False
                    },
                    {
                        'content': 'Your Moon sign reveals your emotional needs, instinctive reactions, and inner world. It shows how you process feelings, what makes you feel secure, and your subconscious patterns. This is often considered more revealing of your true self than your Sun sign.',
                        'is_ai': True,
                        'tokens_used': 52
                    }
                ]
            }
        ]

        for session_data in demo_sessions:
            session = ChatSession.objects.create(
                user=demo_user,
                title=session_data['title'],
                context_notes=session_data['context_notes']
            )

            for message_data in session_data['messages']:
                ChatMessage.objects.create(
                    session=session,
                    content=message_data['content'],
                    is_ai=message_data['is_ai'],
                    tokens_used=message_data.get('tokens_used', 0)
                )

        self.stdout.write(
            self.style.SUCCESS('Demo data setup complete')
        )

    def process_documents(self):
        """Process all pending documents in the knowledge base"""
        self.stdout.write('Processing pending documents...')

        knowledge_service = KnowledgeService()
        pending_docs = knowledge_service.get_pending_documents()

        if not pending_docs:
            self.stdout.write('No pending documents to process')
            return

        processed_count = 0
        for doc in pending_docs:
            try:
                knowledge_service.process_document(doc)
                processed_count += 1
                self.stdout.write(f'  ✓ Processed: {doc.title}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed to process {doc.title}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Processed {processed_count} documents')
        )

    def cleanup_old_data(self):
        """Clean up old sessions and documents"""
        self.stdout.write('Cleaning up old data...')

        from django.utils import timezone
        from datetime import timedelta
        from plugins.astrology_chat.models import ChatSession, ChatMessage

        # Delete sessions older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        old_sessions = ChatSession.objects.filter(created_at__lt=cutoff_date)
        session_count = old_sessions.count()
        old_sessions.delete()

        # Delete messages older than 90 days
        old_messages = ChatMessage.objects.filter(created_at__lt=cutoff_date)
        message_count = old_messages.count()
        old_messages.delete()

        self.stdout.write(
            self.style.SUCCESS(f'Cleaned up {session_count} sessions and {message_count} messages')
        )

    def check_requirements(self):
        """Check if all requirements are met"""
        self.stdout.write('Checking requirements...')

        # Check if required packages are installed
        try:
            import openai
            self.stdout.write('  ✓ OpenAI package available')
        except ImportError:
            self.stdout.write(
                self.style.WARNING('  ⚠ OpenAI package not found')
            )

        try:
            import anthropic
            self.stdout.write('  ✓ Anthropic package available')
        except ImportError:
            self.stdout.write(
                self.style.WARNING('  ⚠ Anthropic package not found')
            )

        # Check environment variables
        required_vars = [
            'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY',
            'OPENROUTER_API_KEY'
        ]

        for var in required_vars:
            if os.getenv(var):
                self.stdout.write(f'  ✓ {var} is set')
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ {var} is not set')
                )

        self.stdout.write(
            self.style.SUCCESS('Requirements check complete')
        )
