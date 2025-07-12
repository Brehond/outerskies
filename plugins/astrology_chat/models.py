from django.db import models
from django.utils import timezone
import uuid


class ChatSession(models.Model):
    """
    Model to store chat sessions for astrology consultations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('chart.User', on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, default="New Chat Session")

    # Session context
    chart_data = models.JSONField(null=True, blank=True, help_text="Associated natal chart data")
    context_notes = models.TextField(blank=True, help_text="Additional context for the AI")

    # Session metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)

    # Usage tracking
    message_count = models.IntegerField(default=0)
    total_tokens_used = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    class Meta:
        db_table = 'astrology_chat_session'
        ordering = ['-last_activity']
        verbose_name = 'Chat Session'
        verbose_name_plural = 'Chat Sessions'

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    @property
    def messages(self):
        """Get all messages for this session"""
        return self.chat_messages.all()

    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class ChatMessage(models.Model):
    """
    Model to store individual chat messages
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey('chart.User', on_delete=models.CASCADE, related_name='chat_messages')

    # Message content
    content = models.TextField()
    is_ai = models.BooleanField(default=False, help_text="Whether this message is from the AI")

    # Message metadata
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('user', 'User Message'),
            ('ai', 'AI Response'),
            ('system', 'System Message'),
        ],
        default='user'
    )

    # AI response metadata
    ai_model_used = models.CharField(max_length=50, blank=True)
    tokens_used = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    response_time = models.FloatField(default=0, help_text="Response time in seconds")

    # Knowledge base references
    knowledge_sources = models.JSONField(default=list, help_text="References to knowledge base documents used")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'astrology_chat_message'
        ordering = ['created_at']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'

    def __str__(self):
        return f"{self.session.title} - {self.content[:50]}..."

    def save(self, *args, **kwargs):
        """Override save to update session activity and message count"""
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Update session message count
            self.session.message_count = self.session.messages.count()
            self.session.save(update_fields=['message_count'])

            # Update session activity
            self.session.update_activity()


class KnowledgeCategory(models.Model):
    """
    Model to categorize knowledge base documents
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6", help_text="Hex color for category")
    order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'astrology_knowledge_category'
        ordering = ['order', 'name']
        verbose_name = 'Knowledge Category'
        verbose_name_plural = 'Knowledge Categories'

    def __str__(self):
        return self.name


class KnowledgeDocument(models.Model):
    """
    Model to store knowledge base documents for AI reference
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Document metadata
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(KnowledgeCategory, on_delete=models.SET_NULL, null=True, blank=True)

    # Document content
    content = models.TextField(help_text="Processed text content of the document")
    original_content = models.TextField(blank=True, help_text="Original unprocessed content")

    # File information
    file_path = models.CharField(max_length=500, blank=True, help_text="Path to original file")
    file_type = models.CharField(
        max_length=20,
        choices=[
            ('pdf', 'PDF'),
            ('docx', 'Word Document'),
            ('txt', 'Text File'),
            ('md', 'Markdown'),
            ('html', 'HTML'),
        ],
        default='txt'
    )
    file_size = models.IntegerField(default=0, help_text="File size in bytes")

    # Processing metadata
    is_processed = models.BooleanField(default=False, help_text="Whether document has been processed for search")
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    processing_error = models.TextField(blank=True, help_text="Error message if processing failed")

    # Search and embedding metadata
    embedding_id = models.CharField(max_length=100, blank=True, help_text="ID in vector database")
    chunk_count = models.IntegerField(default=0, help_text="Number of text chunks created")

    # Document status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True, help_text="Whether document is available to all users")

    # Ownership
    uploaded_by = models.ForeignKey('chart.User', on_delete=models.SET_NULL, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'astrology_knowledge_document'
        ordering = ['-created_at']
        verbose_name = 'Knowledge Document'
        verbose_name_plural = 'Knowledge Documents'

    def __str__(self):
        return self.title

    @property
    def word_count(self):
        """Get approximate word count"""
        return len(self.content.split()) if self.content else 0

    @property
    def is_accessible(self):
        """Check if document is accessible to current user"""
        return self.is_active and (self.is_public or self.uploaded_by is not None)


class ChatAnalytics(models.Model):
    """
    Model to track chat usage analytics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('chart.User', on_delete=models.CASCADE, related_name='chat_analytics')

    # Daily usage tracking
    date = models.DateField()
    sessions_created = models.IntegerField(default=0)
    messages_sent = models.IntegerField(default=0)
    ai_responses_received = models.IntegerField(default=0)

    # Token and cost tracking
    total_tokens_used = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    # Knowledge base usage
    knowledge_searches = models.IntegerField(default=0)
    knowledge_documents_accessed = models.IntegerField(default=0)

    # Performance metrics
    avg_response_time = models.FloatField(default=0, help_text="Average AI response time in seconds")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'astrology_chat_analytics'
        unique_together = ['user', 'date']
        ordering = ['-date']
        verbose_name = 'Chat Analytics'
        verbose_name_plural = 'Chat Analytics'

    def __str__(self):
        return f"{self.user.username} - {self.date}"
