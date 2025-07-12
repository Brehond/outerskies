from django import forms
from django.contrib.auth import get_user_model
from .models import ChatMessage, KnowledgeDocument, KnowledgeCategory

User = get_user_model()


class ChatMessageForm(forms.ModelForm):
    """
    Form for sending chat messages
    """
    class Meta:
        model = ChatMessage
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Ask about your natal chart, planetary positions, aspects, or any astrological question...',
                'maxlength': 2000,
            })
        }

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if not content or not content.strip():
            raise forms.ValidationError("Message cannot be empty.")

        if len(content.strip()) < 3:
            raise forms.ValidationError("Message must be at least 3 characters long.")

        if len(content) > 2000:
            raise forms.ValidationError("Message cannot exceed 2000 characters.")

        return content.strip()


class KnowledgeDocumentForm(forms.ModelForm):
    """
    Form for uploading knowledge base documents
    """
    file = forms.FileField(
        required=True,
        help_text="Upload a PDF, Word document, or text file",
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            'accept': '.pdf,.docx,.txt,.md,.html'
        })
    )

    class Meta:
        model = KnowledgeDocument
        fields = ['title', 'description', 'category', 'is_public']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Enter document title...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Brief description of the document content...'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = KnowledgeCategory.objects.all().order_by('order', 'name')

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size cannot exceed 10MB.")

            # Check file type
            allowed_types = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'text/markdown', 'text/html']
            if file.content_type not in allowed_types:
                raise forms.ValidationError("Only PDF, Word documents, and text files are allowed.")

            # Check file extension
            allowed_extensions = ['.pdf', '.docx', '.txt', '.md', '.html']
            import os
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError("Invalid file extension. Allowed: PDF, DOCX, TXT, MD, HTML")

        return file

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise forms.ValidationError("Title is required.")

        if len(title.strip()) < 3:
            raise forms.ValidationError("Title must be at least 3 characters long.")

        if len(title) > 255:
            raise forms.ValidationError("Title cannot exceed 255 characters.")

        return title.strip()


class ChatSessionForm(forms.Form):
    """
    Form for creating or editing chat sessions
    """
    title = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter session title...'
        })
    )

    context_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'rows': 4,
            'placeholder': 'Optional: Add context about your natal chart or specific questions you want to explore...'
        })
    )

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise forms.ValidationError("Title is required.")

        if len(title.strip()) < 3:
            raise forms.ValidationError("Title must be at least 3 characters long.")

        return title.strip()


class KnowledgeSearchForm(forms.Form):
    """
    Form for searching the knowledge base
    """
    query = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Search astrology knowledge base...'
        })
    )

    category = forms.ModelChoiceField(
        queryset=KnowledgeCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = KnowledgeCategory.objects.all().order_by('order', 'name')


class ChatSettingsForm(forms.Form):
    """
    Form for chat settings and preferences
    """
    preferred_ai_model = forms.ChoiceField(
        choices=[
            ('gpt-4', 'GPT-4 (Most Capable)'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Fast & Efficient)'),
            ('claude-3-opus', 'Claude-3 Opus (Analytical)'),
            ('claude-3-sonnet', 'Claude-3 Sonnet (Balanced)'),
            ('mistral-medium', 'Mistral Medium (Open Source)'),
        ],
        required=True,
        initial='gpt-4',
        widget=forms.Select(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    response_length = forms.ChoiceField(
        choices=[
            ('concise', 'Concise (100-200 words)'),
            ('detailed', 'Detailed (300-500 words)'),
            ('comprehensive', 'Comprehensive (500+ words)'),
        ],
        required=True,
        initial='detailed',
        widget=forms.Select(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        })
    )

    include_knowledge_base = forms.BooleanField(
        required=False,
        help_text="Include knowledge base documents in AI responses",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        })
    )

    auto_save_sessions = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Automatically save chat sessions",
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        })
    )
