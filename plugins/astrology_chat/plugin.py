from plugins.base import BasePlugin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
import json
import logging
from .models import ChatSession, ChatMessage, KnowledgeDocument
from .forms import ChatMessageForm
from .services.chat_service import ChatService
from .services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

# Create a plugin instance for view functions
_plugin_instance = None


def get_plugin_instance():
    """Get the plugin instance for view functions"""
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = AstrologyChatPlugin()
    return _plugin_instance


# Wrapper functions for view methods
@login_required
def chat_dashboard_view(request):
    """Wrapper for chat dashboard view"""
    return get_plugin_instance().chat_dashboard(request)


@login_required
def chat_session_view(request, session_id):
    """Wrapper for chat session view"""
    return get_plugin_instance().chat_session(request, session_id)


@login_required
def new_chat_session_view(request):
    """Wrapper for new chat session view"""
    return get_plugin_instance().new_chat_session(request)


@login_required
@require_http_methods(["POST"])
def send_message_view(request, session_id):
    """Wrapper for send message view"""
    return get_plugin_instance().send_message(request, session_id)


@login_required
def delete_session_view(request, session_id):
    """Wrapper for delete session view"""
    return get_plugin_instance().delete_session(request, session_id)


@login_required
def knowledge_base_view(request):
    """Wrapper for knowledge base view"""
    return get_plugin_instance().knowledge_base(request)


@login_required
def upload_document_view(request):
    """Wrapper for upload document view"""
    return get_plugin_instance().upload_document(request)


@login_required
def view_document_view(request, doc_id):
    """Wrapper for view document view"""
    return get_plugin_instance().view_document(request, doc_id)


@login_required
def api_sessions_view(request):
    """Wrapper for API sessions view"""
    return get_plugin_instance().api_sessions(request)


@login_required
def api_messages_view(request, session_id):
    """Wrapper for API messages view"""
    return get_plugin_instance().api_messages(request, session_id)


@login_required
def api_send_message_view(request, session_id):
    """Wrapper for API send message view"""
    return get_plugin_instance().api_send_message(request, session_id)


@login_required
def api_knowledge_search_view(request):
    """Wrapper for API knowledge search view"""
    return get_plugin_instance().api_knowledge_search(request)


class AstrologyChatPlugin(BasePlugin):
    name = "Astrology Chat"
    version = "1.0.0"
    description = "AI-powered chat functionality for natal chart analysis with knowledge base integration"
    author = "Outer Skies Team"
    website = "https://outer-skies.com"

    requires_auth = True
    admin_enabled = True
    api_enabled = True

    def install(self):
        """Install the astrology chat plugin"""
        self.log("Installing Astrology Chat Plugin")

        # Create default knowledge base categories
        from .models import KnowledgeCategory
        default_categories = [
            "Planetary Meanings",
            "House Interpretations",
            "Aspect Analysis",
            "Zodiac Signs",
            "Traditional Astrology",
            "Modern Astrology",
            "Techniques & Methods"
        ]

        for category_name in default_categories:
            KnowledgeCategory.objects.get_or_create(name=category_name)

        return True

    def uninstall(self):
        """Uninstall the astrology chat plugin"""
        self.log("Uninstalling Astrology Chat Plugin")
        # Clean up chat sessions and messages
        ChatSession.objects.all().delete()
        ChatMessage.objects.all().delete()
        return True

    def get_urls(self):
        """Return URL patterns for the astrology chat"""
        return [
            path('chat/', chat_dashboard_view, name='astrology_chat_dashboard'),
            path('chat/session/<uuid:session_id>/', chat_session_view, name='astrology_chat_session'),
            path('chat/new/', new_chat_session_view, name='new_chat_session'),
            path('chat/session/<uuid:session_id>/send/', send_message_view, name='send_chat_message'),
            path('chat/session/<uuid:session_id>/delete/', delete_session_view, name='delete_chat_session'),
            path('chat/knowledge/', knowledge_base_view, name='knowledge_base'),
            path('chat/knowledge/upload/', upload_document_view, name='upload_knowledge_document'),
            path('chat/knowledge/<uuid:doc_id>/', view_document_view, name='view_knowledge_document'),
        ]

    def get_admin_urls(self):
        """Return admin URL patterns"""
        return [
            path('admin/chat/', self.admin_dashboard, name='chat_admin_dashboard'),
            path('admin/chat/sessions/', self.admin_sessions, name='chat_admin_sessions'),
            path('admin/chat/knowledge/', self.admin_knowledge, name='chat_admin_knowledge'),
        ]

    def get_api_urls(self):
        """Return API URL patterns"""
        return [
            path('api/chat/sessions/', api_sessions_view, name='api_chat_sessions'),
            path('api/chat/session/<uuid:session_id>/messages/', api_messages_view, name='api_chat_messages'),
            path('api/chat/session/<uuid:session_id>/send/', api_send_message_view, name='api_send_message'),
            path('api/chat/knowledge/search/', api_knowledge_search_view, name='api_knowledge_search'),
        ]

    def get_navigation_items(self, request):
        """Add chat to navigation for premium users"""
        if hasattr(request.user, 'is_premium') and request.user.is_premium:
            return [
                {
                    'name': 'Astrology Chat',
                    'url': '/chat/',
                    'icon': 'chat',
                    'order': 200,
                }
            ]
        return []

    def get_dashboard_widgets(self, request):
        """Add chat widget to dashboard for premium users"""
        if hasattr(request.user, 'is_premium') and request.user.is_premium:
            recent_sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')[:3]
            return [
                {
                    'name': 'Recent Chat Sessions',
                    'template': 'astrology_chat/widgets/recent_sessions.html',
                    'context': {'recent_sessions': recent_sessions},
                    'order': 2,
                }
            ]
        return []

    def get_models(self):
        """Return plugin models"""
        from .models import ChatSession, ChatMessage, KnowledgeDocument, KnowledgeCategory
        return [ChatSession, ChatMessage, KnowledgeDocument, KnowledgeCategory]

    def get_forms(self):
        """Return plugin forms"""
        from .forms import ChatMessageForm, KnowledgeDocumentForm
        return [ChatMessageForm, KnowledgeDocumentForm]

    def get_requirements(self):
        """Return additional Python requirements"""
        return [
            'openai>=1.0.0',
            'anthropic>=0.7.0',
            'langchain>=0.1.0',
            'chromadb>=0.4.0',
            'sentence-transformers>=2.2.0',
            'pypdf>=3.0.0',
            'python-docx>=0.8.11',
        ]

    def chat_dashboard(self, request):
        """Main chat dashboard view"""
        sessions = ChatSession.objects.filter(user=request.user).order_by('-last_activity')
        paginator = Paginator(sessions, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'sessions': page_obj,
            'total_sessions': sessions.count(),
            'active_sessions': sessions.filter(is_active=True).count(),
        }
        return render(request, 'astrology_chat/dashboard.html', context)

    def chat_session(self, request, session_id):
        """Individual chat session view"""
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            django_messages.error(request, "Chat session not found.")
            return redirect('astrology_chat_dashboard')

        messages = session.messages.all()
        form = ChatMessageForm()

        context = {
            'session': session,
            'messages': messages,
            'form': form,
        }
        return render(request, 'astrology_chat/session.html', context)

    def new_chat_session(self, request):
        """Create a new chat session"""
        session = ChatSession.objects.create(
            user=request.user,
            title="New Chat Session"
        )
        return redirect('astrology_chat_session', session_id=session.id)

    def send_message(self, request, session_id):
        """Send a message in a chat session"""
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)

        form = ChatMessageForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data['content']

            # Save user message
            user_message = ChatMessage.objects.create(
                session=session,
                user=request.user,
                content=content,
                is_ai=False
            )

            # Get AI response
            chat_service = ChatService()
            try:
                ai_response = chat_service.generate_response(session, content)
                return JsonResponse({
                    'success': True,
                    'user_message': {
                        'id': str(user_message.id),
                        'content': content,
                        'timestamp': user_message.created_at.isoformat()
                    },
                    'ai_response': {
                        'content': ai_response,
                        'tokens_used': 0,  # Will be updated by the service
                        'response_time': 0  # Will be updated by the service
                    }
                })
            except Exception as e:
                logger.error(f"Error getting AI response: {e}")
                return JsonResponse({
                    'error': 'Failed to get AI response. Please try again.'
                }, status=500)
        else:
            return JsonResponse({'error': 'Invalid message'}, status=400)

    def delete_session(self, request, session_id):
        """Delete a chat session"""
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            session.delete()
            django_messages.success(request, "Chat session deleted successfully.")
        except ChatSession.DoesNotExist:
            django_messages.error(request, "Chat session not found.")
        return redirect('astrology_chat_dashboard')

    def knowledge_base(self, request):
        """Knowledge base view"""
        documents = KnowledgeDocument.objects.filter(is_active=True)
        if not request.user.is_staff:
            documents = documents.filter(is_public=True)

        # Search functionality
        query = request.GET.get('q')
        if query:
            documents = documents.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )

        paginator = Paginator(documents, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'documents': page_obj,
            'search_query': query,
        }
        return render(request, 'astrology_chat/knowledge_base.html', context)

    def upload_document(self, request):
        """Upload a knowledge base document"""
        if request.method == 'POST':
            from .forms import KnowledgeDocumentForm
            form = KnowledgeDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                document = form.save(commit=False)
                document.uploaded_by = request.user
                document.save()
                django_messages.success(request, "Document uploaded successfully.")
                return redirect('knowledge_base')
        else:
            form = KnowledgeDocumentForm()

        context = {'form': form}
        return render(request, 'astrology_chat/upload_document.html', context)

    def view_document(self, request, doc_id):
        """View a knowledge base document"""
        try:
            document = KnowledgeDocument.objects.get(id=doc_id, is_active=True)
            if not document.is_public and document.uploaded_by != request.user:
                django_messages.error(request, "Access denied.")
                return redirect('knowledge_base')
        except KnowledgeDocument.DoesNotExist:
            django_messages.error(request, "Document not found.")
            return redirect('knowledge_base')

        context = {'document': document}
        return render(request, 'astrology_chat/view_document.html', context)

    def api_sessions(self, request):
        """API endpoint for chat sessions"""
        sessions = ChatSession.objects.filter(user=request.user).order_by('-last_activity')
        data = [{
            'id': str(session.id),
            'title': session.title,
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'message_count': session.message_count,
        } for session in sessions]
        return JsonResponse({'sessions': data})

    def api_messages(self, request, session_id):
        """API endpoint for session messages"""
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            messages = session.messages.all()
            data = [{
                'id': str(msg.id),
                'content': msg.content,
                'is_ai': msg.is_ai,
                'created_at': msg.created_at.isoformat(),
                'tokens_used': msg.tokens_used,
            } for msg in messages]
            return JsonResponse({'messages': data})
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)

    def api_send_message(self, request, session_id):
        """API endpoint for sending messages"""
        return self.send_message(request, session_id)

    def api_knowledge_search(self, request):
        """API endpoint for knowledge base search"""
        query = request.GET.get('q', '')
        if not query:
            return JsonResponse({'error': 'Query parameter required'}, status=400)

        knowledge_service = KnowledgeService()
        results = knowledge_service.search(query, limit=10)

        data = [{
            'id': doc.id,
            'title': doc.title,
            'description': doc.description,
            'category': doc.category.name if doc.category else None,
            'relevance_score': getattr(doc, 'relevance_score', 0),
        } for doc in results]

        return JsonResponse({'results': data})

    def admin_dashboard(self, request):
        """Admin dashboard for chat analytics"""
        return render(request, 'astrology_chat/admin/dashboard.html')

    def admin_sessions(self, request):
        """Admin view for managing chat sessions"""
        return render(request, 'astrology_chat/admin/sessions.html')

    def admin_knowledge(self, request):
        """Admin view for managing knowledge base"""
        return render(request, 'astrology_chat/admin/knowledge.html')
