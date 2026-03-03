from django.contrib import admin
from django.utils import timezone
from .models import Category, Product, Cart, Order, Review, Profile, Banner
from .utils import send_order_status_email


admin.site.register(Category)
admin.site.register(Cart)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'quantity', 'selling_price', 'is_veg', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active', 'is_veg', 'category')
    search_fields = ('name', 'category__name')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'orderitem', 'qty', 'order_sts', 'date_order', 'tracking_no')
    list_editable = ('order_sts',)
    list_filter = ('order_sts', 'date_order')
    search_fields = ('tracking_no', 'customer__username')
    ordering = ('date_order',)

    def save_model(self, request, obj, form, change):
        """
        Called when saving from the Order DETAIL page.
        Detects status changes and sends email to the customer.
        """
        old_status = None
        if change and obj.pk:
            try:
                old_status = Order.objects.get(pk=obj.pk).order_sts
            except Order.DoesNotExist:
                pass

        # Update the status_updated_at timestamp when status changes
        if old_status and old_status != obj.order_sts:
            obj.status_updated_at = timezone.now()

        super().save_model(request, obj, form, change)

        # Send email notification if status changed
        if old_status and old_status != obj.order_sts:
            sent = send_order_status_email(obj)
            if sent:
                self.message_user(
                    request,
                    f'✅ Status changed to "{obj.order_sts}" — Email notification sent to {obj.customer.email}.',
                )
            else:
                self.message_user(
                    request,
                    f'⚠️ Status changed to "{obj.order_sts}" but email could not be sent (check email settings).',
                    level='warning',
                )

    def response_change(self, request, obj):
        """Called after saving from the detail change page — just use save_model."""
        return super().response_change(request, obj)

    def changelist_view(self, request, extra_context=None):
        """
        Called after list view including list_editable saves.
        We intercept the POST, snapshot old statuses BEFORE saving,
        then send emails for any that changed.
        """
        # Snapshot current statuses BEFORE the changelist processes POST
        if request.method == 'POST':
            old_statuses = {}
            for order in Order.objects.only('id', 'order_sts', 'status_updated_at'):
                old_statuses[order.id] = order.order_sts

            # Let Django process the changelist save normally
            extra_context = extra_context or {}
            extra_context['revenue_dashboard_link'] = '/calculation/'
            response = super().changelist_view(request, extra_context=extra_context)

            # After save, check for status changes and send emails
            changed_orders = []
            for order in Order.objects.select_related('customer').all():
                prev_status = old_statuses.get(order.id)
                if prev_status and prev_status != order.order_sts:
                    # Update status_updated_at
                    Order.objects.filter(pk=order.pk).update(status_updated_at=timezone.now())
                    send_order_status_email(order)
                    changed_orders.append(
                        f'Order #{order.id} ({order.tracking_no}): "{prev_status}" → "{order.order_sts}"'
                    )

            if changed_orders:
                for msg in changed_orders:
                    self.message_user(request, f'📧 Email sent — {msg}')

            return response

        extra_context = extra_context or {}
        extra_context['revenue_dashboard_link'] = '/calculation/'
        return super().changelist_view(request, extra_context=extra_context)


admin.site.site_header = "LOL Cafe Admin"
admin.site.site_title = "LOL Cafe Admin Portal"
admin.site.index_title = "Welcome to LOL Cafe Management"

admin.site.register(Review)
admin.site.register(Profile)
# admin.site.register(Banner)
