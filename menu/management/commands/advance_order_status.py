from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from menu.models import Order


STATUS_CHAIN = [
    'waiting for accept',
    'accepted and cooking',
    'ready to pickup',
    'Delivered',
]

STATUS_EMAILS = {
    'accepted and cooking': {
        'subject': '🍳 Your LOL Cafe order is being cooked!',
        'body': (
            'Hi {name},\n\n'
            'Great news! Your order #{tracking} is now being prepared by our kitchen.\n'
            'Status: Accepted & Cooking 🍳\n\n'
            'We\'ll notify you when it\'s ready for pickup.\n\n'
            '- LOL Cafe Team'
        )
    },
    'ready to pickup': {
        'subject': '🛍️ Your LOL Cafe order is ready for pickup!',
        'body': (
            'Hi {name},\n\n'
            'Your order #{tracking} is ready! 🎉\n'
            'Status: Ready to Pickup 🛍️\n\n'
            'Please collect your order from the counter.\n\n'
            '- LOL Cafe Team'
        )
    },
    'Delivered': {
        'subject': '✅ Your LOL Cafe order has been delivered!',
        'body': (
            'Hi {name},\n\n'
            'Your order #{tracking} has been marked as Delivered. 🎉\n\n'
            'We hope you enjoyed your meal! Don\'t forget to leave a review.\n\n'
            'Thank you for choosing LOL Cafe! 🍽️\n\n'
            '- LOL Cafe Team'
        )
    },
}


class Command(BaseCommand):
    help = 'Automatically advance order statuses every 5 minutes and send email notifications.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=5,
            help='Minutes threshold before advancing status (default: 5)'
        )

    def handle(self, *args, **options):
        minutes = options['minutes']
        threshold_time = timezone.now() - timezone.timedelta(minutes=minutes)

        # Get all active orders (not Delivered, not Cancelled)
        active_orders = Order.objects.filter(
            order_sts__in=['waiting for accept', 'accepted and cooking', 'ready to pickup']
        ).filter(
            status_updated_at__lte=threshold_time
        )

        advanced_count = 0
        for order in active_orders:
            current_status = order.order_sts
            try:
                current_idx = STATUS_CHAIN.index(current_status)
            except ValueError:
                self.stdout.write(self.style.WARNING(
                    f'Order #{order.id} has unknown status "{current_status}", skipping.'
                ))
                continue

            # Check if there's a next status
            if current_idx < len(STATUS_CHAIN) - 1:
                next_status = STATUS_CHAIN[current_idx + 1]
                order.order_sts = next_status
                order.status_updated_at = timezone.now()
                order.save()

                advanced_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Order #{order.id} ({order.tracking_no}): "{current_status}" → "{next_status}"'
                ))

                # Send email notification
                email_data = STATUS_EMAILS.get(next_status)
                if email_data and order.customer.email:
                    try:
                        body = email_data['body'].format(
                            name=order.customer.username,
                            tracking=order.tracking_no or order.id
                        )
                        send_mail(
                            email_data['subject'],
                            body,
                            settings.EMAIL_HOST_USER,
                            [order.customer.email],
                            fail_silently=False,
                        )
                        self.stdout.write(f'  → Email sent to {order.customer.email}')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  → Email failed: {e}'))

        if advanced_count == 0:
            self.stdout.write('No orders needed status update right now.')
        else:
            self.stdout.write(self.style.SUCCESS(f'\nDone! Advanced {advanced_count} order(s).'))
