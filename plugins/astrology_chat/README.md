# Astrology Chat Plugin

A premium plugin for Outer Skies that provides AI-powered chat functionality for natal chart analysis with an integrated knowledge base of astrology documents.

## 🌟 Features

### Chat Functionality
- **AI-Powered Conversations**: Chat with AI about your natal chart, planetary positions, aspects, and astrological concepts
- **Session Management**: Create, manage, and organize multiple chat sessions
- **Real-time Responses**: Get instant AI responses with typing indicators
- **Chart Integration**: Link your natal chart data for personalized insights
- **Message History**: Full conversation history with timestamps and metadata

### Knowledge Base Integration
- **Document Upload**: Upload PDF, Word documents, and text files
- **Automatic Processing**: Documents are automatically processed and indexed for search
- **Semantic Search**: AI searches through knowledge base to provide informed responses
- **Category Organization**: Organize documents by astrology topics
- **Source Attribution**: AI responses include references to source documents

### Premium Features
- **Premium User Access**: Chat functionality restricted to premium users
- **Usage Analytics**: Track message counts, token usage, and costs
- **Advanced Settings**: Customize AI model, response length, and knowledge base usage
- **Session Analytics**: Detailed insights into chat session patterns

## 🏗️ Architecture

### Models
- `ChatSession`: Manages chat sessions with user and chart data
- `ChatMessage`: Individual messages with AI response metadata
- `KnowledgeDocument`: Stored documents with processing status
- `KnowledgeCategory`: Document categorization system
- `ChatAnalytics`: Usage tracking and analytics

### Services
- `ChatService`: Handles AI interactions and response generation
- `KnowledgeService`: Manages document processing and search functionality

### Key Components
- **Vector Database**: Simple JSON-based storage (upgradeable to ChromaDB)
- **Document Processing**: PDF, DOCX, and text file extraction
- **Text Chunking**: Overlapping text chunks for better search
- **Relevance Scoring**: Keyword-based search with relevance ranking

## 🚀 Installation

### 1. Install Dependencies
```bash
pip install langchain chromadb sentence-transformers pypdf python-docx
```

### 2. Add to Django Settings
Add the plugin to your `INSTALLED_APPS` in `settings.py`:
```python
INSTALLED_APPS = [
    # ... existing apps
    'plugins.astrology_chat',
]
```

### 3. Run Migrations
```bash
python manage.py makemigrations astrology_chat
python manage.py migrate
```

### 4. Install Plugin
```bash
python manage.py manage_plugins install astrology_chat
```

## 📋 Configuration

### Environment Variables
```bash
# Required for AI functionality
OPENROUTER_API_KEY=your_openrouter_api_key

# Optional: Vector database path
VECTOR_DB_PATH=/path/to/vector/database
```

### Settings
The plugin can be configured through Django settings:
```python
# Astrology Chat Settings
ASTROLOGY_CHAT = {
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_FILE_TYPES': ['pdf', 'docx', 'txt', 'md', 'html'],
    'CHUNK_SIZE': 1000,
    'CHUNK_OVERLAP': 200,
    'MAX_SEARCH_RESULTS': 5,
    'DEFAULT_AI_MODEL': 'gpt-4',
    'PREMIUM_REQUIRED': True,
}
```

## 🎯 Usage

### For Users

#### Starting a Chat Session
1. Navigate to the Astrology Chat dashboard
2. Click "New Chat" to create a session
3. Optionally link your natal chart for personalized insights
4. Start asking questions about astrology

#### Using the Knowledge Base
1. Browse documents in the Knowledge Base
2. Search for specific topics or concepts
3. Upload your own astrology documents
4. AI will reference relevant documents in responses

#### Chat Features
- **Real-time Messaging**: Type and send messages instantly
- **Chart Context**: AI considers your natal chart when available
- **Source References**: AI cites knowledge base documents
- **Session Management**: Organize conversations by topic

### For Administrators

#### Managing Documents
1. Access the Knowledge Base admin interface
2. Upload and categorize documents
3. Monitor processing status
4. Review and edit document metadata

#### Analytics
- Track user engagement and usage patterns
- Monitor AI response quality and costs
- Analyze knowledge base effectiveness
- Generate usage reports

## 🔧 Development

### Adding New Features

#### Custom AI Models
```python
# In chat_service.py
def add_custom_model(self, model_name, model_config):
    self.available_models[model_name] = model_config
```

#### Custom Document Processors
```python
# In knowledge_service.py
def add_document_processor(self, file_type, processor_func):
    self.processors[file_type] = processor_func
```

### Extending the Knowledge Base

#### Adding New Categories
```python
from plugins.astrology_chat.models import KnowledgeCategory

category = KnowledgeCategory.objects.create(
    name="Advanced Techniques",
    description="Advanced astrological techniques and methods",
    color="#FF6B6B"
)
```

#### Custom Search Algorithms
```python
# Override search method in KnowledgeService
def custom_search(self, query, **kwargs):
    # Implement custom search logic
    pass
```

## 📊 Analytics and Monitoring

### Usage Metrics
- **Session Count**: Number of chat sessions created
- **Message Volume**: Total messages sent and received
- **Token Usage**: AI token consumption and costs
- **Response Times**: Average AI response times
- **Knowledge Base Usage**: Document access and search patterns

### Performance Monitoring
- **Processing Times**: Document processing efficiency
- **Search Performance**: Query response times
- **Error Rates**: Failed requests and processing errors
- **User Engagement**: Session duration and message frequency

## 🔒 Security and Privacy

### Data Protection
- **User Isolation**: Users can only access their own chat sessions
- **Document Privacy**: Control document visibility and access
- **Secure Uploads**: File validation and virus scanning
- **Data Retention**: Configurable data retention policies

### Premium Access Control
- **User Verification**: Premium status verification
- **Rate Limiting**: Prevent abuse of AI services
- **Cost Monitoring**: Track and limit usage costs
- **Access Logging**: Comprehensive audit trails

## 🚀 Future Enhancements

### Planned Features
- **Advanced Vector Database**: Integration with ChromaDB or Pinecone
- **Semantic Search**: Embedding-based document search
- **Multi-language Support**: International astrology texts
- **Voice Chat**: Audio-based chat interactions
- **Chart Visualization**: Interactive chart displays in chat
- **Collaborative Sessions**: Multi-user chat sessions

### Technical Improvements
- **Async Processing**: Background document processing
- **Caching**: Response and search result caching
- **API Versioning**: Stable API endpoints
- **WebSocket Support**: Real-time chat updates
- **Mobile Optimization**: Responsive mobile interface

## 🐛 Troubleshooting

### Common Issues

#### Document Processing Fails
- Check file format and size limits
- Verify file permissions
- Review processing logs for errors
- Ensure required dependencies are installed

#### AI Responses Slow
- Check OpenRouter API status
- Monitor token usage and limits
- Review network connectivity
- Consider model selection optimization

#### Search Not Working
- Verify document processing status
- Check vector database integrity
- Review search query format
- Monitor search performance metrics

### Debug Mode
Enable debug logging in Django settings:
```python
LOGGING = {
    'loggers': {
        'plugins.astrology_chat': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## 📞 Support

For technical support or feature requests:
- Create an issue in the project repository
- Contact the development team
- Check the documentation and FAQ
- Review the troubleshooting guide

## 📄 License

This plugin is part of the Outer Skies project and follows the same licensing terms.

---

**Note**: This plugin requires a premium subscription and OpenRouter API access to function properly. 