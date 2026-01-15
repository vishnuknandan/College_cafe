from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F
from django.views import View
from django.views.generic import ListView
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.conf import settings
import random
import string

from django.contrib.auth.models import User
from .forms import UserRegisterForm, UserLoginForm, UserOrderForm, ReviewForm, UserUpdateForm, ProfileUpdateForm
from .models import Category, Product, Cart, Order, Review, Profile


# ------------------------ LOGIN REQUIRED DECORATOR ------------------------

def signin_required(fn):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return fn(request, *args, **kwargs)
    return wrapper


# ------------------------ AUTH VIEWS ------------------------

@method_decorator(never_cache, name="dispatch")
class UserRegisterView(View):
    def get(self, request):
        form = UserRegisterForm()
        return render(request, "menu/register.html", {"form": form})

    def post(self, request):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect("login")
        return render(request, "menu/register.html", {"form": form})


@method_decorator(never_cache, name="dispatch")
class UserLoginView(View):
    def get(self, request):
        form = UserLoginForm()
        return render(request, "menu/login.html", {"form": form})

    def post(self, request):
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # Try to handle email login
            if '@' in username_or_email:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    username = user_obj.username
                except User.DoesNotExist:
                    username = username_or_email # Fallback to literal string
            else:
                username = username_or_email

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_superuser:
                    return redirect('/admin/')
                return redirect("home")
            messages.error(request, "Invalid username/email or password")

        return render(request, "menu/login.html", {"form": form})


def UserLogoutView(request):
    logout(request)
    return redirect("login")


# ------------------------ HOME / CATEGORY / PRODUCT ------------------------

# ------------------------ HOME / CATEGORY / PRODUCT ------------------------

@method_decorator(never_cache, name="dispatch")
class HomeView(ListView):
    model = Category
    template_name = "menu/index.html"
    context_object_name = "categories"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Offer Zone: Products with discount > 50% (selling price <= 50% of original price)
        context['offer_products'] = Product.objects.filter(
            original_price__gt=0,
            selling_price__lte=F('original_price') * 0.5
        )
        return context


@method_decorator(never_cache, name="dispatch")
class CategoryDetailView(View):
    def get(self, request, pk):
        category = Category.objects.get(id=pk)
        products = Product.objects.filter(category=category)
        return render(request, "menu/category_detail.html", {
            "name": category,
            "data": products
        })


@method_decorator(never_cache, name="dispatch")
class ProductDetailView(View):
    def get(self, request, pk):
        product = Product.objects.get(id=pk)
        return render(request, "menu/p_detail.html", {"data": product})


# ------------------------ CART FUNCTIONALITY ------------------------

@method_decorator(signin_required, name="dispatch")
class AddToCartView(View):
    def get(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        
        try:
            qty = int(request.GET.get('qty', 1))
            if qty < 1:
                qty = 1
        except ValueError:
            qty = 1

        # Stock Check
        if product.quantity < qty:
            messages.error(request, f"Only {product.quantity} items available!")
            return redirect("product_detail", pk=pk) # Redirect back to product

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            item=product
        )

        if not created:
            if product.quantity < (cart_item.qty + qty):
                 messages.error(request, f"Not enough stock to add {qty} more!")
                 return redirect("cart")
            cart_item.qty += qty
            cart_item.save()
        else:
            cart_item.qty = qty
            cart_item.save()

        messages.success(request, f"{qty} item(s) added to cart!")
        return redirect("cart")


@method_decorator(signin_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class CartView(View):
    def get(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        total = sum(item.item.selling_price * item.qty for item in cart_items)

        return render(request, "menu/cart.html", {
            "data": cart_items,
            "total_price": total
        })


# ------------------------ UPDATE CART QUANTITY ------------------------

@method_decorator(signin_required, name="dispatch")
class IncreaseQty(View):
    def post(self, request, pk):
        item = get_object_or_404(Cart, id=pk, user=request.user)
        
        # Check stock availability
        if item.item.quantity > item.qty:
            item.qty += 1
            item.save()
        else:
            messages.warning(request, f"Only {item.item.quantity} units available.")
            
        return redirect("cart")


@method_decorator(signin_required, name="dispatch")
class DecreaseQty(View):
    def post(self, request, pk):
        item = get_object_or_404(Cart, id=pk, user=request.user)

        if item.qty > 1:
            item.qty -= 1
            item.save()
        else:
            item.delete()
        return redirect("cart")


@method_decorator(signin_required, name="dispatch")
class DeleteCartItemView(View):
    def get(self, request, pk):
        Cart.objects.filter(id=pk, user=request.user).delete()
        messages.warning(request, "Item removed from cart")
        return redirect("cart")


# ------------------------ CHECKOUT & PAYMENTS ------------------------

@method_decorator(signin_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class CheckoutView(View):
    def get(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            messages.warning(request, "Your cart is empty.")
            return redirect("home")

        total = sum(item.item.selling_price * item.qty for item in cart_items)
        form = UserOrderForm()
        
        return render(request, "menu/checkout.html", {
            "cart_items": cart_items,
            "total_price": total,
            "form": form
        })

    def post(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items:
            return redirect("home")

        form = UserOrderForm(request.POST)
        if form.is_valid():
            # address removed as per user request
            
            # Generate unique tracking number for this checkout session
            trackno = 'foodspot' + str(random.randint(1111111, 9999999))
            while Order.objects.filter(tracking_no=trackno).exists():
                trackno = 'foodspot' + str(random.randint(1111111, 9999999))

            # Stock Validation and Order Creation
            total = 0
            for c_item in cart_items:
                if c_item.item.quantity < c_item.qty:
                    messages.error(request, f"Not enough stock for {c_item.item.name}")
                    return redirect("cart")

                # Decrement Stock
                c_item.item.quantity -= c_item.qty
                c_item.item.save()

                # Create Order
                total += c_item.item.selling_price * c_item.qty
                Order.objects.create(
                    orderitem=c_item.item,
                    customer=request.user,
                    qty=c_item.qty,
                    price=c_item.item.selling_price * c_item.qty,
                    order_sts="Pending",
                    tracking_no=trackno
                )
            
            # Clear cart
            cart_items.delete()

            # Send Email Notification
            subject = f"Order Placed Successfully - {trackno}"
            message = f"Hi {request.user.username},\n\nYour order has been placed successfully.\nOrder ID: {trackno}\nTotal Amount: ₹{total}\n\nThank you for ordering with us!\n\nUse 'My Orders' to track status."
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') else 'admin@foodspot.com', [request.user.email])
            except Exception as e:
                print(f"Email failed: {e}")

            return redirect("order_success")

        total = sum(item.item.selling_price * item.qty for item in cart_items)
        return render(request, "menu/checkout.html", {
            "cart_items": cart_items,
            "total_price": total,
            "form": form
        })


@method_decorator(signin_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class BuyNowView(View):
    def get(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        
        try:
            qty = int(request.GET.get('qty', 1))
            if qty < 1:
                qty = 1
        except ValueError:
            qty = 1

        # Stock Check
        if product.quantity < qty:
            messages.error(request, f"Only {product.quantity} units available")
            return redirect("product_detail", pk=pk)
            
        form = UserOrderForm()
        total_price = product.selling_price * qty
        
        return render(request, "menu/buy.html", {
            "product": product, 
            "form": form,
            "qty": qty,
            "total_price": total_price
        })

    def post(self, request, pk):
        form = UserOrderForm(request.POST)
        product = get_object_or_404(Product, id=pk)
        
        try:
            qty = int(request.POST.get('qty', 1))
            if qty < 1:
                qty = 1
        except ValueError:
            qty = 1

        if form.is_valid():
            # address removed as per user request
            
            # Stock Validation Check
            if product.quantity < qty:
                messages.error(request, f"Not enough stock. Only {product.quantity} available.")
                return redirect("home")

            # Generate unique tracking number
            trackno = 'foodspot' + str(random.randint(1111111, 9999999))
            while Order.objects.filter(tracking_no=trackno).exists():
                trackno = 'foodspot' + str(random.randint(1111111, 9999999))

            # Decrement Stock
            product.quantity -= qty
            product.save()

            # Create Order
            current_total = product.selling_price * qty
            Order.objects.create(
                orderitem=product,
                customer=request.user,
                price=current_total,
                order_sts="Pending",
                qty=qty,
                tracking_no=trackno
            )

            # Send Email Notification
            subject = f"Order Placed Successfully - {trackno}"
            message = f"Hi {request.user.username},\n\nYour order for {qty}x {product.name} has been placed successfully.\nOrder ID: {trackno}\nTotal Amount: ₹{current_total}\n\nThank you for ordering with us!"
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') else 'admin@foodspot.com', [request.user.email])
            except Exception as e:
                print(f"Email failed: {e}")

            return redirect("order_success")
        
        total_price = product.selling_price * qty
        return render(request, "menu/buy.html", {
            "product": product, 
            "form": form,
            "qty": qty,
            "total_price": total_price
        })


# ------------------------ ORDER STATUS + HISTORY ------------------------

@method_decorator(signin_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class UserOrdersView(View):
    def get(self, request):
        orders = Order.objects.filter(customer=request.user).order_by("-date_order")
        form = ReviewForm()
        return render(request, "menu/orders.html", {"orders": orders, "form": form})

@method_decorator(signin_required, name="dispatch")
class AddReviewView(View):
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, customer=request.user)
        # Ensure only delivered orders can be reviewed and only once
        if order.order_sts.lower() != "delivered":
             messages.error(request, "You can only review delivered orders.")
             return redirect("my_orders")
        
        if Review.objects.filter(order=order).exists():
            messages.warning(request, "You have already reviewed this order.")
            return redirect("my_orders")

        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = order.orderitem
            review.order = order
            review.save()
            messages.success(request, "Thank you for your feedback!")
        else:
            messages.error(request, "Invalid feedback submission.")
        return redirect("my_orders")


# ------------------------ SEARCH ------------------------

class SearchView(View):
    def get(self, request):
        query = request.GET.get("q")
        products = Product.objects.filter(name__icontains=query) if query else None
        return render(request, "menu/search.html", {"result": products})


@method_decorator(signin_required, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class ProfileView(View):
    def get(self, request):
        u_form = UserUpdateForm(instance=request.user)
        profile, created = Profile.objects.get_or_create(user=request.user)
        p_form = ProfileUpdateForm(instance=profile)
        
        return render(request, 'menu/profile.html', {
            'u_form': u_form,
            'p_form': p_form
        })

    def post(self, request):
        u_form = UserUpdateForm(request.POST, instance=request.user)
        profile, created = Profile.objects.get_or_create(user=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
            
        return render(request, 'menu/profile.html', {
            'u_form': u_form,
            'p_form': p_form
        })


@method_decorator(signin_required, name="dispatch")
class DeleteAccountView(View):
    def post(self, request):
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been deleted permanentally.")
        return redirect("login")


# ------------------------ ORDER SUCCESS PAGE ------------------------

@signin_required
def order_success(request):
    return render(request, "menu/order_success.html")
