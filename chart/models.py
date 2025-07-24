# models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import re


def validate_coordinates(value):
    """Validate coordinate values"""
    if not -180 <= value <= 180:
        raise ValidationError('Coordinate must be between -180 and 180 degrees')


def validate_latitude(value):
    """Validate latitude values"""
    if not -90 <= value <= 90:
        raise ValidationError('Latitude must be between -90 and 90 degrees')


def validate_birth_date(value):
    """Validate birth date is not in the future"""
    if value > timezone.now().date():
        raise ValidationError('Birth date cannot be in the future')


def validate_email_format(value):
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValidationError('Invalid email format')


class User(AbstractUser):
    """
    Extended user model with astrological profile information
    """
    # Basic profile fields
    birth_date = models.DateField(
        null=True, 
        blank=True, 
        validators=[validate_birth_date],
        help_text="User's birth date for personalized features"
    )
    birth_time = models.TimeField(null=True, blank=True, help_text="User's birth time for accurate chart calculations")
    birth_location = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="User's birth location"
    )
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True, 
        validators=[validate_latitude],
        help_text="Birth latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True, 
        validators=[validate_coordinates],
        help_text="Birth longitude"
    )
    timezone = models.CharField(
        max_length=50, 
        default='UTC', 
        help_text="User's timezone"
    )

    # Astrological preferences
    preferred_zodiac_type = models.CharField(
        max_length=20,
        choices=[('tropical', 'Tropical'), ('sidereal', 'Sidereal')],
        default='tropical',
        help_text="Preferred zodiac system"
    )
    preferred_house_system = models.CharField(
        max_length=20,
        choices=[('placidus', 'Placidus'), ('whole_sign', 'Whole Sign')],
        default='placidus',
        help_text="Preferred house system"
    )
    preferred_ai_model = models.CharField(
        max_length=50,
        default='gpt-4',
        help_text="Preferred AI model for interpretations"
    )

    # Account settings
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)

    # Privacy settings
    profile_public = models.BooleanField(default=False, help_text="Allow others to view profile")
    chart_history_public = models.BooleanField(default=False, help_text="Allow others to view chart history")
    # Premium access
    is_premium = models.BooleanField(default=False, help_text="User has premium access")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'chart_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        constraints = [
            models.CheckConstraint(
                check=models.Q(latitude__isnull=True) | models.Q(latitude__gte=-90, latitude__lte=90),
                name='valid_latitude_range'
            ),
            models.CheckConstraint(
                check=models.Q(longitude__isnull=True) | models.Q(longitude__gte=-180, longitude__lte=180),
                name='valid_longitude_range'
            ),
            models.CheckConstraint(
                check=models.Q(birth_date__isnull=True) | models.Q(birth_date__lte=timezone.now().date()),
                name='birth_date_not_future'
            ),
        ]

    def __str__(self):
        return self.username or self.email

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate email format
        if self.email:
            validate_email_format(self.email)
        
        # Validate coordinate consistency
        if self.latitude is not None and self.longitude is not None:
            if not (-90 <= float(self.latitude) <= 90):
                raise ValidationError({'latitude': 'Latitude must be between -90 and 90 degrees'})
            if not (-180 <= float(self.longitude) <= 180):
                raise ValidationError({'longitude': 'Longitude must be between -180 and 180 degrees'})

    @property
    def has_birth_data(self):
        """Check if user has complete birth data for chart generation"""
        return all([self.birth_date, self.birth_time, self.latitude, self.longitude])

    def get_birth_data_dict(self):
        """Get birth data as dictionary for chart generation"""
        if not self.has_birth_data:
            return None

        return {
            'date': self.birth_date.strftime('%Y-%m-%d'),
            'time': self.birth_time.strftime('%H:%M'),
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'location': self.birth_location,
            'timezone': self.timezone,
            'zodiac_type': self.preferred_zodiac_type,
            'house_system': self.preferred_house_system
        }


class Chart(models.Model):
    """
    Model to store generated astrological charts
    """
    # Chart identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='charts')
    name = models.CharField(max_length=255, blank=True, help_text="User-defined chart name")

    # Birth data
    birth_date = models.DateField(validators=[validate_birth_date])
    birth_time = models.TimeField()
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        validators=[validate_latitude]
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        validators=[validate_coordinates]
    )
    location_name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=50)

    # Chart settings
    zodiac_type = models.CharField(
        max_length=20, 
        choices=[('tropical', 'Tropical'), ('sidereal', 'Sidereal')]
    )
    house_system = models.CharField(
        max_length=20, 
        choices=[('placidus', 'Placidus'), ('whole_sign', 'Whole Sign')]
    )
    ai_model_used = models.CharField(max_length=50)

    # Chart data (JSON fields)
    chart_data = models.JSONField(help_text="Raw chart calculation data")
    planetary_positions = models.JSONField(help_text="Planetary positions and aspects")
    house_positions = models.JSONField(help_text="House cusps and signs")
    aspects = models.JSONField(help_text="Planetary aspects")

    # Interpretations
    interpretation = models.TextField(blank=True, help_text="AI-generated interpretation")
    interpretation_tokens_used = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        help_text="Number of tokens used for interpretation"
    )
    interpretation_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        default=0, 
        validators=[MinValueValidator(0)],
        help_text="Cost of interpretation"
    )

    # Chart visualization
    chart_image = models.ImageField(upload_to='charts/', null=True, blank=True, help_text="Generated chart image")

    # Metadata
    is_public = models.BooleanField(default=False, help_text="Allow public access to this chart")
    is_favorite = models.BooleanField(default=False, help_text="User's favorite chart")
    tags = models.JSONField(default=list, help_text="User-defined tags for organization")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chart'
        ordering = ['-created_at']
        verbose_name = 'Chart'
        verbose_name_plural = 'Charts'
        constraints = [
            models.CheckConstraint(
                check=models.Q(latitude__gte=-90, latitude__lte=90),
                name='chart_valid_latitude'
            ),
            models.CheckConstraint(
                check=models.Q(longitude__gte=-180, longitude__lte=180),
                name='chart_valid_longitude'
            ),
            models.CheckConstraint(
                check=models.Q(birth_date__lte=timezone.now().date()),
                name='chart_birth_date_not_future'
            ),
            models.CheckConstraint(
                check=models.Q(interpretation_tokens_used__gte=0),
                name='chart_positive_tokens'
            ),
            models.CheckConstraint(
                check=models.Q(interpretation_cost__gte=0),
                name='chart_positive_cost'
            ),
        ]
        indexes = [
            # User and time-based queries
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'is_favorite', 'created_at']),
            models.Index(fields=['user', 'zodiac_type', 'house_system']),
            
            # Birth data queries
            models.Index(fields=['birth_date', 'birth_time']),
            models.Index(fields=['latitude', 'longitude']),
            
            # Public and visibility queries
            models.Index(fields=['is_public']),
            models.Index(fields=['is_favorite']),
            models.Index(fields=['zodiac_type', 'house_system']),
            
            # JSON field indexes for PostgreSQL (optimized queries)
            models.Index(fields=['planetary_positions'], name='idx_chart_planetary_positions'),
            models.Index(fields=['house_positions'], name='idx_chart_house_positions'),
            models.Index(fields=['aspects'], name='idx_chart_aspects'),
            
            # Performance indexes for common queries
            models.Index(fields=['created_at', 'user']),
            models.Index(fields=['updated_at', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name or self.birth_date}"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Validate coordinate consistency
        if not (-90 <= float(self.latitude) <= 90):
            raise ValidationError({'latitude': 'Latitude must be between -90 and 90 degrees'})
        if not (-180 <= float(self.longitude) <= 180):
            raise ValidationError({'longitude': 'Longitude must be between -180 and 180 degrees'})

    @property
    def chart_summary(self):
        """Get a summary of the chart for display"""
        if self.planetary_positions:
            sun_sign = self.planetary_positions.get('Sun', {}).get('sign', 'Unknown')
            moon_sign = self.planetary_positions.get('Moon', {}).get('sign', 'Unknown')
            ascendant = self.house_positions.get('ascendant', {}).get('sign', 'Unknown')
            return f"Sun: {sun_sign}, Moon: {moon_sign}, Asc: {ascendant}"
        return "Chart data not available"


class UserSession(models.Model):
    """
    Track user sessions for security and analytics
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_session'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"


class PasswordResetToken(models.Model):
    """
    Secure password reset tokens
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_token'
        indexes = [
            models.Index(fields=['token', 'is_used']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.token[:8]}..."

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class TaskStatus(models.Model):
    """
    Model to track background task status and progress.
    """
    TASK_TYPES = [
        ('chart_generation', 'Chart Generation'),
        ('interpretation', 'AI Interpretation'),
        ('ephemeris', 'Ephemeris Calculation'),
        ('plugin_processing', 'Plugin Processing'),
    ]

    TASK_STATES = [
        ('PENDING', 'Pending'),
        ('PROGRESS', 'In Progress'),
        ('SUCCESS', 'Completed'),
        ('FAILURE', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    task_id = models.CharField(max_length=255, unique=True, help_text="Celery task ID")
    task_type = models.CharField(max_length=50, choices=TASK_TYPES, help_text="Type of task")
    state = models.CharField(max_length=20, choices=TASK_STATES, default='PENDING')
    progress = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Progress percentage (0-100)"
    )
    status_message = models.TextField(blank=True, help_text="Current status message")

    # Task parameters (stored as JSON)
    parameters = models.JSONField(default=dict, help_text="Task input parameters")

    # Task results (stored as JSON)
    result = models.JSONField(default=dict, help_text="Task output results")

    # Error information
    error_message = models.TextField(blank=True, help_text="Error message if task failed")
    traceback = models.TextField(blank=True, help_text="Full error traceback")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # User association (optional)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'chart_task_status'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['task_type', 'state']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['state', 'created_at']),
            models.Index(fields=['progress']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(progress__gte=0, progress__lte=100),
                name='task_progress_range'
            ),
        ]

    def __str__(self):
        return f"{self.task_type} - {self.task_id} ({self.state})"

    @property
    def duration(self):
        """Calculate task duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None

    @property
    def is_completed(self):
        """Check if task is completed"""
        return self.state in ['SUCCESS', 'FAILURE', 'CANCELLED']

    @property
    def is_running(self):
        """Check if task is running"""
        return self.state == 'PROGRESS'

    def update_progress(self, progress, status_message=""):
        """Update task progress"""
        if not 0 <= progress <= 100:
            raise ValidationError("Progress must be between 0 and 100")
        
        self.progress = progress
        if status_message:
            self.status_message = status_message
        self.save(update_fields=['progress', 'status_message', 'updated_at'])

    def mark_completed(self, result=None, error_message="", traceback=""):
        """Mark task as completed"""
        self.state = 'SUCCESS' if not error_message else 'FAILURE'
        self.completed_at = timezone.now()
        if result:
            self.result = result
        if error_message:
            self.error_message = error_message
        if traceback:
            self.traceback = traceback
        self.progress = 100
        self.save()

    def mark_cancelled(self):
        """Mark task as cancelled"""
        self.state = 'CANCELLED'
        self.completed_at = timezone.now()
        self.save()
