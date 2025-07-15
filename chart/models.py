# models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class User(AbstractUser):
    """
    Extended user model with astrological profile information
    """
    # Basic profile fields
    birth_date = models.DateField(null=True, blank=True, help_text="User's birth date for personalized features")
    birth_time = models.TimeField(null=True, blank=True, help_text="User's birth time for accurate chart calculations")
    birth_location = models.CharField(max_length=255, blank=True, help_text="User's birth location")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Birth latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Birth longitude")
    timezone = models.CharField(max_length=50, default='UTC', help_text="User's timezone")

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

    def __str__(self):
        return self.username or self.email

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
    birth_date = models.DateField()
    birth_time = models.TimeField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    location_name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=50)

    # Chart settings
    zodiac_type = models.CharField(max_length=20, choices=[('tropical', 'Tropical'), ('sidereal', 'Sidereal')])
    house_system = models.CharField(max_length=20, choices=[('placidus', 'Placidus'), ('whole_sign', 'Whole Sign')])
    ai_model_used = models.CharField(max_length=50)

    # Chart data (JSON fields)
    chart_data = models.JSONField(help_text="Raw chart calculation data")
    planetary_positions = models.JSONField(help_text="Planetary positions and aspects")
    house_positions = models.JSONField(help_text="House cusps and signs")
    aspects = models.JSONField(help_text="Planetary aspects")

    # Interpretations
    interpretation = models.TextField(blank=True, help_text="AI-generated interpretation")
    interpretation_tokens_used = models.IntegerField(default=0, help_text="Number of tokens used for interpretation")
    interpretation_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0, help_text="Cost of interpretation")

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

    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"


class PasswordResetToken(models.Model):
    """
    Secure password reset tokens
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_token'

    def __str__(self):
        return f"Reset token for {self.user.username}"

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
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
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
            models.Index(fields=['task_type']),
            models.Index(fields=['state']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.task_type} - {self.task_id} ({self.state})"

    @property
    def duration(self):
        """Calculate task duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or timezone.now()
        return (end_time - self.started_at).total_seconds()

    @property
    def is_completed(self):
        """Check if task is in a final state."""
        return self.state in ['SUCCESS', 'FAILURE', 'CANCELLED']

    @property
    def is_running(self):
        """Check if task is currently running."""
        return self.state == 'PROGRESS'

    def update_progress(self, progress, status_message=""):
        """Update task progress and status."""
        self.progress = progress
        self.status_message = status_message
        if self.state == 'PENDING':
            self.state = 'PROGRESS'
            self.started_at = timezone.now()
        self.save()

    def mark_completed(self, result=None, error_message="", traceback=""):
        """Mark task as completed."""
        self.state = 'SUCCESS' if not error_message else 'FAILURE'
        self.completed_at = timezone.now()
        if result:
            self.result = result
        if error_message:
            self.error_message = error_message
        if traceback:
            self.traceback = traceback
        self.save()

    def mark_cancelled(self):
        """Mark task as cancelled."""
        self.state = 'CANCELLED'
        self.completed_at = timezone.now()
        self.save()
