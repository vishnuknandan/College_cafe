from django.core.management.base import BaseCommand
from django.utils import timezone
from menu.models import Order
from menu.utils import send_order_status_email


STATUS_CHAIN = [
    'waiting for accept',
    'accepted and cooking',
    'ready to pickup',
    'Delivered',
]


class Command(BaseCommand):
    help = 'Automatically advance order statuses every N minutes and send email notifications.'

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

        # Get all active orders not yet Delivered or Cancelled
        active_orders = Order.objects.filter(
            order_sts__in=['waiting for accept', 'accepted and cooking', 'ready to pickup']
        ).filter(
            status_updated_at__lte=threshold_time
        ).select_related('customer')

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

            if current_idx < len(STATUS_CHAIN) - 1:
                next_status = STATUS_CHAIN[current_idx + 1]
                order.order_sts = next_status
                order.status_updated_at = timezone.now()
                order.save()

                advanced_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Order #{order.id} ({order.tracking_no}): "{current_status}" → "{next_status}"'
                ))

                # Send email notification using shared utility
                sent = send_order_status_email(order)
                if sent:
                    self.stdout.write(f'  → Email sent to {order.customer.email}')
                else:
                    self.stdout.write(self.style.WARNING(f'  → Email failed for {order.customer.email}'))

        if advanced_count == 0:
            self.stdout.write('No orders needed status update right now.')
        else:
            self.stdout.write(self.style.SUCCESS(f'\nDone! Advanced {advanced_count} order(s).'))
