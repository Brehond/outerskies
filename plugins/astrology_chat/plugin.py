from plugins.base import BasePlugin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
            path('chat/', self.chat_dashboard, name='astrology_chat_dashboard'),
            path('chat/session/<uuid:session_id>/', self.chat_session, name='astrology_chat_session'),
            path('chat/new/', self.new_chat_session, name='new_chat_session'),
            path('chat/session/<uuid:session_id>/send/', self.send_message, name='send_chat_message'),
            path('chat/session/<uuid:session_id>/delete/', self.delete_session, name='delete_chat_session'),
            path('chat/knowledge/', self.knowledge_base, name='knowledge_base'),
            path('chat/knowledge/upload/', self.upload_document, name='upload_knowledge_document'),
            path('chat/knowledge/<int:doc_id>/', self.view_document, name='view_knowledge_document'),
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
            path('api/chat/sessions/', self.api_sessions, name='api_chat_sessions'),
            path('api/chat/session/<uuid:session_id>/messages/', self.api_messages, name='api_chat_messages'),
            path('api/chat/session/<uuid:session_id>/send/', self.api_send_message, name='api_send_message'),
            path('api/chat/knowledge/search/', self.api_knowledge_search, name='api_knowledge_search'),
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
            'langchain>=0.1.0',
            'chromadb>=0.4.0',
            'sentence-transformers>=2.2.0',
            'pypdf>=3.0.0',
            'python-docx>=0.8.11',
        ]
    
    # View Methods
    @login_required
    def chat_dashboard(self, request):
        """Main chat dashboard"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            messages.warning(request, "Astrology Chat is a premium feature. Please upgrade your account.")
            return redirect('/payments/pricing/')
        
        sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
        paginator = Paginator(sessions, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'astrology_chat/dashboard.html', {
            'sessions': page_obj,
            'total_sessions': sessions.count(),
        })
    
    @login_required
    def chat_session(self, request, session_id):
        """Individual chat session view"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            messages.warning(request, "Astrology Chat is a premium feature. Please upgrade your account.")
            return redirect('/payments/pricing/')
        
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            messages = ChatMessage.objects.filter(session=session).order_by('created_at')
            form = ChatMessageForm()
            
            return render(request, 'astrology_chat/session.html', {
                'session': session,
                'messages': messages,
                'form': form,
            })
        except ChatSession.DoesNotExist:
            messages.error(request, "Chat session not found.")
            return redirect('astrology_chat_dashboard')
    
    @login_required
    def new_chat_session(self, request):
        """Create a new chat session"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            return JsonResponse({'error': 'Premium feature required'}, status=403)
        
        session = ChatSession.objects.create(
            user=request.user,
            title="New Chat Session"
        )
        
        return redirect('astrology_chat_session', session_id=session.id)
    
    @login_required
    @require_http_methods(["POST"])
    def send_message(self, request, session_id):
        """Send a message in a chat session"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            return JsonResponse({'error': 'Premium feature required'}, status=403)
        
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            form = ChatMessageForm(request.POST)
            
            if form.is_valid():
                message = form.save(commit=False)
                message.session = session
                message.user = request.user
                message.save()
                
                # Generate AI response
                chat_service = ChatService()
                ai_response = chat_service.generate_response(session, message.content)
                
                # Save AI response
                ai_message = ChatMessage.objects.create(
                    session=session,
                    user=request.user,
                    content=ai_response,
                    is_ai=True
                )
                
                return JsonResponse({
                    'success': True,
                    'user_message': {
                        'id': message.id,
                        'content': message.content,
                        'created_at': message.created_at.isoformat(),
                    },
                    'ai_message': {
                        'id': ai_message.id,
                        'content': ai_message.content,
                        'created_at': ai_message.created_at.isoformat(),
                    }
                })
            else:
                return JsonResponse({'error': 'Invalid message'}, status=400)
                
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return JsonResponse({'error': 'Internal server error'}, status=500)
    
    @login_required
    def delete_session(self, request, session_id):
        """Delete a chat session"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            return JsonResponse({'error': 'Premium feature required'}, status=403)
        
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            session.delete()
            messages.success(request, "Chat session deleted successfully.")
            return redirect('astrology_chat_dashboard')
        except ChatSession.DoesNotExist:
            messages.error(request, "Chat session not found.")
            return redirect('astrology_chat_dashboard')
    
    @login_required
    def knowledge_base(self, request):
        """Knowledge base view"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            messages.warning(request, "Knowledge base is a premium feature.")
            return redirect('/payments/pricing/')
        
        documents = KnowledgeDocument.objects.filter(is_active=True).order_by('-created_at')
        search_query = request.GET.get('q', '')
        
        if search_query:
            documents = documents.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        paginator = Paginator(documents, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'astrology_chat/knowledge_base.html', {
            'documents': page_obj,
            'search_query': search_query,
        })
    
    @login_required
    def upload_document(self, request):
        """Upload a knowledge document"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            messages.warning(request, "Document upload is a premium feature.")
            return redirect('/payments/pricing/')
        
        if request.method == 'POST':
            from .forms import KnowledgeDocumentForm
            form = KnowledgeDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                document = form.save(commit=False)
                document.uploaded_by = request.user
                document.save()
                
                # Process document content
                knowledge_service = KnowledgeService()
                knowledge_service.process_document(document)
                
                messages.success(request, "Document uploaded and processed successfully.")
                return redirect('knowledge_base')
        else:
            from .forms import KnowledgeDocumentForm
            form = KnowledgeDocumentForm()
        
        return render(request, 'astrology_chat/upload_document.html', {'form': form})
    
    @login_required
    def view_document(self, request, doc_id):
        """View a knowledge document"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            messages.warning(request, "Document viewing is a premium feature.")
            return redirect('/payments/pricing/')
        
        try:
            document = KnowledgeDocument.objects.get(id=doc_id, is_active=True)
            return render(request, 'astrology_chat/view_document.html', {
                'document': document
            })
        except KnowledgeDocument.DoesNotExist:
            messages.error(request, "Document not found.")
            return redirect('knowledge_base')
    
    # API Methods
    @login_required
    def api_sessions(self, request):
        """API endpoint for chat sessions"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            return JsonResponse({'error': 'Premium feature required'}, status=403)
        
        sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
        data = [{
            'id': str(session.id),
            'title': session.title,
            'created_at': session.created_at.isoformat(),
            'message_count': session.messages.count(),
        } for session in sessions]
        
        return JsonResponse({'sessions': data})
    
    @login_required
    def api_messages(self, request, session_id):
        """API endpoint for chat messages"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            return JsonResponse({'error': 'Premium feature required'}, status=403)
        
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            messages = ChatMessage.objects.filter(session=session).order_by('created_at')
            data = [{
                'id': msg.id,
                'content': msg.content,
                'is_ai': msg.is_ai,
                'created_at': msg.created_at.isoformat(),
            } for msg in messages]
            
            return JsonResponse({'messages': data})
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
    
    @login_required
    def api_send_message(self, request, session_id):
        """API endpoint for sending messages"""
        return self.send_message(request, session_id)
    
    @login_required
    def api_knowledge_search(self, request):
        """API endpoint for knowledge base search"""
        if not hasattr(request.user, 'is_premium') or not request.user.is_premium:
            return JsonResponse({'error': 'Premium feature required'}, status=403)
        
        query = request.GET.get('q', '')
        if not query:
            return JsonResponse({'error': 'Query parameter required'}, status=400)
        
        knowledge_service = KnowledgeService()
        results = knowledge_service.search(query, limit=10)
        
        return JsonResponse({'results': results}) 