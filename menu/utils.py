from django.core.mail import send_mail
from django.conf import settings


# Email templates for each order status transition
ORDER_STATUS_EMAILS = {
    'waiting for accept': {
        'subject': '⏳ LOL Cafe — Order Received!',
        'body': (
            'Hi {name},\n\n'
            'We have received your order #{tracking}. ⏳\n'
            'Status: Waiting for Acceptance\n\n'
            'Our team will confirm your order shortly.\n\n'
            '- LOL Cafe Team'
        )
    },
    'accepted and cooking': {
        'subject': '🍳 LOL Cafe — Your order is being cooked!',
        'body': (
            'Hi {name},\n\n'
            'Great news! Your order #{tracking} has been accepted and is now being prepared by our kitchen. 🍳\n'
            'Status: Accepted & Cooking\n\n'
            'We\'ll notify you when it\'s ready for pickup.\n\n'
            '- LOL Cafe Team'
        )
    },
    'ready to pickup': {
        'subject': '🛍️ LOL Cafe — Your order is ready for pickup!',
        'body': (
            'Hi {name},\n\n'
            'Your order #{tracking} is ready! 🎉\n'
            'Status: Ready to Pickup 🛍️\n\n'
            'Please collect your order from the counter.\n\n'
            '- LOL Cafe Team'
        )
    },
    'Delivered': {
        'subject': '✅ LOL Cafe — Your order has been delivered!',
        'body': (
            'Hi {name},\n\n'
            'Your order #{tracking} has been marked as Delivered. 🎉\n\n'
            'We hope you enjoyed your meal! Don\'t forget to leave a review.\n\n'
            'Thank you for choosing LOL Cafe! 🍽️\n\n'
            '- LOL Cafe Team'
        )
    },
    'Cancelled': {
        'subject': '❌ LOL Cafe — Your order has been cancelled.',
        'body': (
            'Hi {name},\n\n'
            'We\'re sorry to inform you that your order #{tracking} has been cancelled. ❌\n\n'
            'If you have any questions, please contact us.\n\n'
            '- LOL Cafe Team'
        )
    },
}


def send_order_status_email(order):
    """
    Sends an email to the customer notifying them of the current order status.
    Handles all status transitions including Cancelled.
    """
    email = order.customer.email
    if not email:
        return

    email_data = ORDER_STATUS_EMAILS.get(order.order_sts)
    if not email_data:
        return

    try:
        body = email_data['body'].format(
            name=order.customer.username,
            tracking=order.tracking_no or f'#{order.id}'
        )
        send_mail(
            email_data['subject'],
            body,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f'[LOL Cafe] Order status email failed for order #{order.id}: {e}')
        return False
