from rest_framework import serializers
from chart.models import User, Chart, TaskStatus
from django.contrib.auth import authenticate
from payments.models import SubscriptionPlan, UserSubscription, Payment, Coupon
from drf_spectacular.utils import extend_schema_field, OpenApiTypes

# Import chat models if they exist
def get_chat_models():
    from plugins.astrology_chat.models import ChatSession, ChatMessage, KnowledgeDocument
    return ChatSession, ChatMessage, KnowledgeDocument

try:
    ChatSession, ChatMessage, KnowledgeDocument = get_chat_models()
    CHAT_AVAILABLE = True
except ImportError:
    CHAT_AVAILABLE = False
    ChatSession = None
    ChatMessage = None
    KnowledgeDocument = None


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    charts_count = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'birth_date', 'birth_time', 'birth_location', 'latitude', 'longitude',
            'timezone', 'preferred_zodiac_type', 'preferred_house_system',
            'preferred_ai_model', 'email_verified', 'profile_public',
            'chart_history_public', 'is_premium', 'created_at', 'updated_at',
            'charts_count', 'subscription_status'
        ]
        read_only_fields = ['id', 'email_verified', 'is_premium', 'created_at', 'updated_at']
    
    @extend_schema_field(OpenApiTypes.INT)
    def get_charts_count(self, obj):
        return obj.charts.count()
    
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_subscription_status(self, obj) -> dict:
        if hasattr(obj, 'subscription'):
            return {
                'plan_name': obj.subscription.plan.name,
                'status': obj.subscription.status,
                'is_active': obj.subscription.is_active,
                'current_period_end': obj.subscription.current_period_end,
                'charts_remaining': obj.subscription.charts_remaining,
                'interpretations_remaining': obj.subscription.interpretations_remaining
            }
        return None


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Password must be at least 8 characters long"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Must match the password field"
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField(help_text="Username or email address")
    password = serializers.CharField(write_only=True, help_text="User password")
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs


class ChartSerializer(serializers.ModelSerializer):
    """Serializer for Chart model"""
    user = UserSerializer(read_only=True)
    chart_summary = serializers.ReadOnlyField()
    
    @extend_schema_field(OpenApiTypes.STR)
    def get_chart_summary(self, obj) -> str:
        return obj.chart_summary
    
    class Meta:
        model = Chart
        fields = [
            'id', 'user', 'name', 'birth_date', 'birth_time', 'latitude', 'longitude',
            'location_name', 'timezone', 'zodiac_type', 'house_system', 'ai_model_used',
            'chart_data', 'planetary_positions', 'house_positions', 'aspects',
            'interpretation', 'interpretation_tokens_used', 'interpretation_cost',
            'chart_image', 'is_public', 'is_favorite', 'tags', 'created_at', 'updated_at',
            'chart_summary'
        ]
        read_only_fields = [
            'id', 'user', 'ai_model_used', 'chart_data', 'planetary_positions',
            'house_positions', 'aspects', 'interpretation', 'interpretation_tokens_used',
            'interpretation_cost', 'chart_image', 'created_at', 'updated_at'
        ]


class ChartGenerationSerializer(serializers.Serializer):
    """Serializer for chart generation requests"""
    birth_date = serializers.DateField(
        help_text="Birth date in YYYY-MM-DD format"
    )
    birth_time = serializers.TimeField(
        help_text="Birth time in HH:MM format (24-hour)"
    )
    latitude = serializers.FloatField(
        min_value=-90, 
        max_value=90,
        help_text="Birth latitude (-90 to 90)"
    )
    longitude = serializers.FloatField(
        min_value=-180, 
        max_value=180,
        help_text="Birth longitude (-180 to 180)"
    )
    location_name = serializers.CharField(
        max_length=255, 
        required=False,
        help_text="Human-readable location name"
    )
    timezone = serializers.CharField(
        max_length=50,
        help_text="Timezone (e.g., 'America/New_York', 'UTC')"
    )
    zodiac_type = serializers.ChoiceField(
        choices=[('tropical', 'Tropical'), ('sidereal', 'Sidereal')],
        help_text="Zodiac system to use"
    )
    house_system = serializers.ChoiceField(
        choices=[('placidus', 'Placidus'), ('whole_sign', 'Whole Sign')],
        help_text="House system to use"
    )
    ai_model = serializers.CharField(
        max_length=50, 
        required=False, 
        default='gpt-4',
        help_text="AI model for interpretation"
    )
    temperature = serializers.FloatField(
        min_value=0.0, 
        max_value=1.0, 
        required=False, 
        default=0.7,
        help_text="AI creativity level (0.0-1.0)"
    )
    max_tokens = serializers.IntegerField(
        min_value=100, 
        max_value=4000, 
        required=False, 
        default=1000,
        help_text="Maximum tokens for AI response"
    )
    interpretation_type = serializers.ChoiceField(
        choices=[('comprehensive', 'Comprehensive'), ('basic', 'Basic'), ('detailed', 'Detailed')],
        required=False, 
        default='comprehensive',
        help_text="Type of interpretation to generate"
    )
    chart_name = serializers.CharField(
        max_length=255, 
        required=False,
        help_text="Optional name for the chart"
    )
    
    def validate(self, attrs):
        # Additional validation logic
        if attrs.get('location_name') is None:
            attrs['location_name'] = f"{attrs['latitude']}, {attrs['longitude']}"
        return attrs


class ChartInterpretationSerializer(serializers.Serializer):
    """Serializer for chart interpretation requests"""
    ai_model = serializers.CharField(max_length=50, required=False, default='gpt-4')
    temperature = serializers.FloatField(min_value=0.0, max_value=1.0, required=False, default=0.7)
    max_tokens = serializers.IntegerField(min_value=100, max_value=4000, required=False, default=1000)
    interpretation_type = serializers.ChoiceField(
        choices=[('comprehensive', 'Comprehensive'), ('basic', 'Basic'), ('detailed', 'Detailed')],
        required=False, default='comprehensive'
    )


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""
    features = serializers.ListField(child=serializers.CharField(), read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'billing_cycle', 'price_monthly', 'price_yearly',
            'charts_per_month', 'ai_interpretations_per_month', 'priority_support',
            'advanced_ai_models', 'chart_history_unlimited', 'export_features',
            'description', 'features', 'is_active', 'is_popular'
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""
    plan = SubscriptionPlanSerializer(read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'user', 'plan', 'status', 'is_active', 'current_period_start',
            'current_period_end', 'charts_remaining', 'interpretations_remaining',
            'created_at', 'updated_at'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment history"""
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'subscription', 'amount', 'currency', 'status',
            'payment_method', 'stripe_payment_intent_id', 'created_at'
        ]


class CouponSerializer(serializers.Serializer):
    """Serializer for coupon validation"""
    code = serializers.CharField(max_length=50)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    discount_type = serializers.CharField(read_only=True)
    discount_value = serializers.CharField(read_only=True)
    currency = serializers.CharField(read_only=True)


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions"""
    class Meta:
        model = ChatSession if CHAT_AVAILABLE else None
        fields = [
            'id', 'user', 'title', 'context_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    class Meta:
        model = ChatMessage if CHAT_AVAILABLE else None
        fields = [
            'id', 'session', 'role', 'content', 'tokens_used', 'cost', 'created_at'
        ]
        read_only_fields = ['id', 'session', 'tokens_used', 'cost', 'created_at']


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """Serializer for knowledge documents"""
    class Meta:
        model = KnowledgeDocument if CHAT_AVAILABLE else None
        fields = [
            'id', 'title', 'content', 'category', 'tags', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AIModelSerializer(serializers.Serializer):
    """Serializer for AI model information"""
    name = serializers.CharField()
    id = serializers.CharField()
    max_tokens = serializers.IntegerField()
    temperature = serializers.FloatField()
    description = serializers.CharField()


class ThemeSerializer(serializers.Serializer):
    """Serializer for theme information"""
    name = serializers.CharField()
    id = serializers.CharField()
    description = serializers.CharField()
    preview_url = serializers.CharField(required=False)


class TaskStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for TaskStatus model.
    """
    duration = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()
    is_running = serializers.SerializerMethodField()
    
    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_duration(self, obj) -> float:
        return obj.duration
    
    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_completed(self, obj) -> bool:
        return obj.is_completed
    
    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_running(self, obj) -> bool:
        return obj.is_running
    
    class Meta:
        model = TaskStatus
        fields = [
            'id', 'task_id', 'task_type', 'state', 'progress', 'status_message',
            'parameters', 'result', 'error_message', 'traceback',
            'created_at', 'started_at', 'completed_at', 'duration',
            'is_completed', 'is_running', 'user'
        ]
        read_only_fields = [
            'id', 'task_id', 'state', 'progress', 'status_message',
            'result', 'error_message', 'traceback',
            'created_at', 'started_at', 'completed_at', 'duration',
            'is_completed', 'is_running'
        ]
    
 