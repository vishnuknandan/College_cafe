from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# ------------------------------ CATEGORY ------------------------------

class Category(models.Model):
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(max_length=200, null=False, blank=False)
    image = models.ImageField(upload_to='images', null=True)
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# ------------------------------ PRODUCT ------------------------------

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, null=False, blank=False)
    product_image = models.ImageField(upload_to='images', null=True, blank=True)
    quantity = models.IntegerField(null=False, blank=False, default=0)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    description = models.TextField(max_length=300, null=False)

    def __str__(self):
        return self.name


# ------------------------------ CART ------------------------------

class Cart(models.Model):
    item = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    qty = models.IntegerField(null=False, default=1)
    date = models.DateTimeField(auto_now_add=True)
    
    def total_price(self):
        return self.qty * self.item.selling_price

    def __str__(self):
        return f"{self.user.username} - {self.item.name}"


# ------------------------------ ORDER ------------------------------

class Order(models.Model):
    orderitem = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    qty = models.IntegerField(default=1) # Kept this to avoid breaking Buy logic
    date_order = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )
    order_sts = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    address = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Razorpay fields (Preserving these as they were in original file, likely needed)
    razorpay_order_id = models.CharField(max_length=200, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=200, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=200, null=True, blank=True)
    tracking_no = models.CharField(max_length=150, null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"


# ------------------------------ REVIEW ------------------------------

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField(default=5)
    comment = models.TextField(max_length=500)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"


# ------------------------------ PROFILE ------------------------------

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, null=True, blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

# Create profile automatically when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
