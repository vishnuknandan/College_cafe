from django.contrib import admin
from .models import Category, Product, Cart, Order, Review, Profile

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Cart)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'orderitem', 'qty', 'order_sts', 'date_order', 'tracking_no')
    list_editable = ('order_sts',)
    list_filter = ('order_sts', 'date_order')
    search_fields = ('tracking_no', 'customer__username')

admin.site.register(Review)
admin.site.register(Profile)
