from django.contrib import admin
from .models import Category, Product, Cart, Order, Review, Profile, Banner

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Cart)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'orderitem', 'qty', 'order_sts', 'date_order', 'tracking_no')
    list_editable = ('order_sts',)
    list_filter = ('order_sts', 'date_order')
    search_fields = ('tracking_no', 'customer__username')
    ordering = ('date_order',)

    # Add a link to calculation at the top of orders list
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['revenue_dashboard_link'] = '/calculation/'
        return super().changelist_view(request, extra_context=extra_context)

admin.site.site_header = "LOL Cafe Admin"
admin.site.site_title = "LOL Cafe Admin Portal"
admin.site.index_title = "Welcome to LOL Cafe Management"

admin.site.register(Review)
admin.site.register(Profile)
# admin.site.register(Banner)
