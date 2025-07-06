from django.core.management.base import BaseCommand
from django.conf import settings
from payments.models import SubscriptionPlan, Coupon
from payments.stripe_utils import create_default_plans
import stripe
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Set up the payment system with default plans and Stripe configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-plans',
            action='store_true',
            help='Create default subscription plans',
        )
        parser.add_argument(
            '--create-coupons',
            action='store_true',
            help='Create sample coupon codes',
        )
        parser.add_argument(
            '--stripe-setup',
            action='store_true',
            help='Set up Stripe products and prices',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all setup steps',
        )

    def handle(self, *args, **options):
        if options['all'] or options['create_plans']:
            self.create_default_plans()
        
        if options['all'] or options['create_coupons']:
            self.create_sample_coupons()
        
        if options['all'] or options['stripe_setup']:
            self.setup_stripe_products()

    def create_default_plans(self):
        """Create default subscription plans"""
        self.stdout.write('Creating default subscription plans...')
        
        try:
            plans = create_default_plans()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {len(plans)} subscription plans')
            )
            
            for plan in plans:
                self.stdout.write(f'  - {plan.name}: ${plan.price_monthly}/month')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating plans: {e}')
            )

    def create_sample_coupons(self):
        """Create sample coupon codes"""
        self.stdout.write('Creating sample coupon codes...')
        
        coupons_data = [
            {
                'code': 'WELCOME20',
                'name': 'Welcome Discount',
                'description': '20% off your first month',
                'discount_type': 'percentage',
                'discount_value': 20,
                'max_uses': 100,
                'valid_from': '2024-01-01',
                'valid_until': '2024-12-31',
            },
            {
                'code': 'ANNUAL10',
                'name': 'Annual Discount',
                'description': '10% off annual subscriptions',
                'discount_type': 'percentage',
                'discount_value': 10,
                'max_uses': 50,
                'valid_from': '2024-01-01',
                'valid_until': '2024-12-31',
            },
            {
                'code': 'FREEMONTH',
                'name': 'Free Month',
                'description': 'One month free on annual plans',
                'discount_type': 'fixed_amount',
                'discount_value': 19.99,
                'max_uses': 25,
                'valid_from': '2024-01-01',
                'valid_until': '2024-06-30',
            }
        ]
        
        created_count = 0
        for coupon_data in coupons_data:
            try:
                from django.utils.dateparse import parse_date
                coupon_data['valid_from'] = parse_date(coupon_data['valid_from'])
                if coupon_data['valid_until']:
                    coupon_data['valid_until'] = parse_date(coupon_data['valid_until'])
                
                coupon, created = Coupon.objects.get_or_create(
                    code=coupon_data['code'],
                    defaults=coupon_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  - Created coupon: {coupon.code}')
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating coupon {coupon_data["code"]}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} coupon codes')
        )

    def setup_stripe_products(self):
        """Set up Stripe products and prices"""
        self.stdout.write('Setting up Stripe products and prices...')
        
        if not settings.STRIPE_SECRET_KEY:
            self.stdout.write(
                self.style.WARNING('STRIPE_SECRET_KEY not configured. Skipping Stripe setup.')
            )
            return
        
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Create products for each plan
            plans = SubscriptionPlan.objects.filter(is_active=True)
            
            for plan in plans:
                if plan.plan_type == 'free':
                    continue  # Skip free plan
                
                # Create or get product
                try:
                    product = stripe.Product.create(
                        name=f"Outer Skies - {plan.name}",
                        description=plan.description,
                        metadata={
                            'plan_id': plan.id,
                            'plan_type': plan.plan_type,
                        }
                    )
                except stripe.error.InvalidRequestError:
                    # Product might already exist, try to find it
                    products = stripe.Product.list(limit=100)
                    product = None
                    for p in products.data:
                        if p.metadata.get('plan_id') == str(plan.id):
                            product = p
                            break
                    
                    if not product:
                        self.stdout.write(
                            self.style.ERROR(f'Could not create or find product for plan {plan.name}')
                        )
                        continue
                
                # Create monthly price
                if plan.price_monthly and plan.price_monthly > 0:
                    try:
                        monthly_price = stripe.Price.create(
                            product=product.id,
                            unit_amount=int(plan.price_monthly * 100),  # Convert to cents
                            currency='usd',
                            recurring={'interval': 'month'},
                            metadata={'plan_id': plan.id, 'billing_cycle': 'monthly'}
                        )
                        plan.stripe_price_id_monthly = monthly_price.id
                        self.stdout.write(f'  - Created monthly price for {plan.name}: ${plan.price_monthly}')
                    except stripe.error.InvalidRequestError:
                        self.stdout.write(
                            self.style.WARNING(f'Monthly price for {plan.name} might already exist')
                        )
                
                # Create yearly price
                if plan.price_yearly and plan.price_yearly > 0:
                    try:
                        yearly_price = stripe.Price.create(
                            product=product.id,
                            unit_amount=int(plan.price_yearly * 100),  # Convert to cents
                            currency='usd',
                            recurring={'interval': 'year'},
                            metadata={'plan_id': plan.id, 'billing_cycle': 'yearly'}
                        )
                        plan.stripe_price_id_yearly = yearly_price.id
                        self.stdout.write(f'  - Created yearly price for {plan.name}: ${plan.price_yearly}')
                    except stripe.error.InvalidRequestError:
                        self.stdout.write(
                            self.style.WARNING(f'Yearly price for {plan.name} might already exist')
                        )
                
                plan.save()
            
            self.stdout.write(
                self.style.SUCCESS('Successfully set up Stripe products and prices')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up Stripe: {e}')
            )

    def check_stripe_configuration(self):
        """Check if Stripe is properly configured"""
        self.stdout.write('Checking Stripe configuration...')
        
        if not settings.STRIPE_SECRET_KEY:
            self.stdout.write(
                self.style.ERROR('STRIPE_SECRET_KEY not configured')
            )
            return False
        
        if not settings.STRIPE_PUBLISHABLE_KEY:
            self.stdout.write(
                self.style.ERROR('STRIPE_PUBLISHABLE_KEY not configured')
            )
            return False
        
        if not settings.STRIPE_WEBHOOK_SECRET:
            self.stdout.write(
                self.style.WARNING('STRIPE_WEBHOOK_SECRET not configured (webhooks will not work)')
            )
        
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            # Test API connection
            stripe.Account.retrieve()
            self.stdout.write(
                self.style.SUCCESS('Stripe configuration is valid')
            )
            return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Stripe configuration error: {e}')
            )
            return False 