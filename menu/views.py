from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import F, Sum, Q
from django.views import View
from django.views.generic import ListView
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import random
import string

from django.contrib.auth.models import User
from .forms import UserRegisterForm, UserLoginForm, UserOrderForm, ReviewForm, UserUpdateForm, ProfileUpdateForm
from .models import Category, Product, Cart, Order, Review, Profile, EmailOTP, Banner, Favorite


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
            email = form.cleaned_data["email"]
            username = form.cleaned_data["username"]

            # Check if email or username already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, "An account with this email already exists.")
                return render(request, "menu/register.html", {"form": form})
            if User.objects.filter(username=username).exists():
                messages.error(request, "This username is already taken.")
                return render(request, "menu/register.html", {"form": form})

            # Generate 6-digit OTP
            otp_code = str(random.randint(100000, 999999))

            # Remove any existing OTP for this email
            EmailOTP.objects.filter(email=email).delete()
            EmailOTP.objects.create(email=email, otp=otp_code)

            # Store registration data in session
            request.session['reg_username'] = username
            request.session['reg_email'] = email
            request.session['reg_password'] = form.cleaned_data["password"]

            # Send OTP email
            subject = "Your LOL Cafe Verification Code"
            message = (
                f"Hi {username},\n\n"
                f"Your verification code is: {otp_code}\n\n"
                f"This code is valid for 10 minutes.\n"
                f"If you did not request this, please ignore this email.\n\n"
                f"- LOL Cafe Team"
            )
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
            except Exception as e:
                print(f"OTP email failed: {e}")
                messages.error(request, "Failed to send OTP. Please try again.")
                return render(request, "menu/register.html", {"form": form})

            messages.success(request, f"A 6-digit code has been sent to {email}. Please verify.")
            return redirect("verify_otp")

        return render(request, "menu/register.html", {"form": form})


@method_decorator(never_cache, name="dispatch")
class VerifyOTPView(View):
    def get(self, request):
        email = request.session.get('reg_email')
        if not email:
            messages.error(request, "Session expired. Please register again.")
            return redirect("register")
        return render(request, "menu/verify_otp.html", {"email": email})

    def post(self, request):
        email = request.session.get('reg_email')
        if not email:
            messages.error(request, "Session expired. Please register again.")
            return redirect("register")

        # Combine the 6 digit inputs
        digits = [
            request.POST.get(f"otp_{i}", "").strip()
            for i in range(1, 7)
        ]
        entered_otp = "".join(digits)

        try:
            otp_record = EmailOTP.objects.filter(email=email).latest('created_at')
        except EmailOTP.DoesNotExist:
            messages.error(request, "OTP not found. Please register again.")
            return redirect("register")

        if otp_record.is_expired():
            otp_record.delete()
            messages.error(request, "OTP has expired. Please register again.")
            # Clear session data
            for key in ['reg_username', 'reg_email', 'reg_password']:
                request.session.pop(key, None)
            return redirect("register")

        if entered_otp != otp_record.otp:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, "menu/verify_otp.html", {"email": email})

        # OTP is valid — create the user
        username = request.session.get('reg_username')
        password = request.session.get('reg_password')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        # Clean up
        otp_record.delete()
        for key in ['reg_username', 'reg_email', 'reg_password']:
            request.session.pop(key, None)

        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")


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
        # Offer Zone: Products with discount >= 50%
        offer_products = Product.objects.filter(
            original_price__gt=0,
            selling_price__lte=F('original_price') * 0.5
        )
        
        context['veg_offers'] = offer_products.filter(is_veg=True)
        context['nonveg_offers'] = offer_products.filter(is_veg=False)
        context['special_offers'] = offer_products # For the "Special Offer" filter tab
        
        # All Active Products for the main grid
        context['all_products'] = Product.objects.filter(quantity__gt=0)
        
        # Get user favorites if authenticated
        if self.request.user.is_authenticated:
            context['user_favorites'] = Favorite.objects.filter(user=self.request.user).values_list('product_id', flat=True)
        else:
            context['user_favorites'] = []
        
        # Fetch Banners for Swipeable Slider
        context['banners'] = Banner.objects.filter(active=True)
        
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
        top_reviews = Review.objects.filter(product=product).select_related('user').order_by('-rating', '-date')[:5]
        similar_products = Product.objects.filter(
            category=product.category,
            quantity__gt=0
        ).exclude(id=product.id)[:8]

        return render(request, "menu/p_detail.html", {
            "data": product,
            "top_reviews": top_reviews,
            "similar_products": similar_products,
        })


# ------------------------ CART FUNCTIONALITY ------------------------

@method_decorator(signin_required, name="dispatch")
class AddToCartView(View):
    def get(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        try:
            qty = int(request.GET.get('qty', 1))
            if qty < 1:
                qty = 1
        except ValueError:
            qty = 1

        # Stock Check
        if product.quantity < qty:
            if is_ajax:
                return JsonResponse({"success": False, "message": f"Only {product.quantity} items available!"})
            messages.error(request, f"Only {product.quantity} items available!")
            return redirect("product_detail", pk=pk)

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            item=product
        )

        if not created:
            if product.quantity < (cart_item.qty + qty):
                if is_ajax:
                    return JsonResponse({"success": False, "message": f"Not enough stock to add {qty} more!"})
                messages.error(request, f"Not enough stock to add {qty} more!")
                return redirect("cart")
            cart_item.qty += qty
            cart_item.save()
        else:
            cart_item.qty = qty
            cart_item.save()

        cart_count = Cart.objects.filter(user=request.user).count()

        if is_ajax:
            return JsonResponse({
                "success": True,
                "message": f"{qty} item(s) added to cart!",
                "cart_count": cart_count,
            })

        messages.success(request, f"{qty} item(s) added to cart!")
        return redirect(request.META.get('HTTP_REFERER', 'home'))


# ------------------------ FAVORITES FUNCTIONALITY ------------------------

@method_decorator(signin_required, name="dispatch")
class AddToFavoriteView(View):
    def get(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        Favorite.objects.get_or_create(user=request.user, product=product)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "favorited": True,
                "product_id": product.id,
            })
        messages.success(request, f"{product.name} added to favorites!")
        return redirect(request.META.get('HTTP_REFERER', 'home'))


@method_decorator(signin_required, name="dispatch")
class RemoveFromFavoriteView(View):
    def get(self, request, pk):
        product = get_object_or_404(Product, id=pk)
        Favorite.objects.filter(user=request.user, product=product).delete()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "favorited": False,
                "product_id": product.id,
            })
        messages.warning(request, f"{product.name} removed from favorites.")
        return redirect(request.META.get('HTTP_REFERER', 'home'))


@method_decorator(signin_required, name="dispatch")
class FavoritesListView(View):
    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user).select_related('product')
        return render(request, "menu/favorites.html", {"favorites": favorites})


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
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        
        # Check stock availability
        if item.item.quantity > item.qty:
            item.qty += 1
            item.save()
            success = True
            message = "Quantity increased."
        else:
            success = False
            message = f"Only {item.item.quantity} units available."
            if not is_ajax:
                messages.warning(request, message)

        if is_ajax:
            total_price = sum(i.qty * i.item.selling_price for i in Cart.objects.filter(user=request.user))
            cart_count = Cart.objects.filter(user=request.user).count()
            return JsonResponse({
                "success": success,
                "message": message,
                "item_qty": item.qty,
                "item_total": item.qty * item.item.selling_price,
                "cart_total": total_price,
                "cart_count": cart_count
            })
            
        return redirect("cart")


@method_decorator(signin_required, name="dispatch")
class DecreaseQty(View):
    def post(self, request, pk):
        item = get_object_or_404(Cart, id=pk, user=request.user)
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

        removed = False
        if item.qty > 1:
            item.qty -= 1
            item.save()
            message = "Quantity decreased."
        else:
            item.delete()
            removed = True
            message = "Item removed from cart."

        if is_ajax:
            total_price = sum(i.qty * i.item.selling_price for i in Cart.objects.filter(user=request.user))
            cart_count = Cart.objects.filter(user=request.user).count()
            return JsonResponse({
                "success": True,
                "message": message,
                "removed": removed,
                "item_qty": 0 if removed else item.qty,
                "item_total": 0 if removed else (item.qty * item.item.selling_price),
                "cart_total": total_price,
                "cart_count": cart_count
            })
            
        return redirect("cart")


@method_decorator(signin_required, name="dispatch")
class DeleteCartItemView(View):
    def get(self, request, pk):
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        Cart.objects.filter(id=pk, user=request.user).delete()
        
        if is_ajax:
            total_price = sum(i.qty * i.item.selling_price for i in Cart.objects.filter(user=request.user))
            cart_count = Cart.objects.filter(user=request.user).count()
            return JsonResponse({
                "success": True,
                "message": "Item removed from cart",
                "cart_total": total_price,
                "cart_count": cart_count
            })

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
                payment_method = request.POST.get('payment_method', 'COD')
                total += c_item.item.selling_price * c_item.qty
                Order.objects.create(
                    orderitem=c_item.item,
                    customer=request.user,
                    qty=c_item.qty,
                    price=c_item.item.selling_price * c_item.qty,
                    order_sts='waiting for accept',
                    tracking_no=trackno,
                    payment_method=payment_method,
                    status_updated_at=timezone.now()
                )
            
            # Clear cart
            cart_items.delete()

            # Send Email Notification
            subject = f"Order Placed Successfully - {trackno}"
            message = f"Hi {request.user.username},\n\nYour order has been placed successfully.\nOrder ID: {trackno}\nPayment: {request.POST.get('payment_method', 'COD')}\nTotal Amount: \u20b9{total}\n\nThank you for ordering with us!\n\nUse 'My Orders' to track status."
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
            payment_method = request.POST.get('payment_method', 'COD')
            current_total = product.selling_price * qty
            Order.objects.create(
                orderitem=product,
                customer=request.user,
                price=current_total,
                order_sts='waiting for accept',
                qty=qty,
                tracking_no=trackno,
                payment_method=payment_method,
                status_updated_at=timezone.now()
            )

            # Send Email Notification
            subject = f"Order Placed Successfully - {trackno}"
            message = f"Hi {request.user.username},\n\nYour order for {qty}x {product.name} has been placed successfully.\nOrder ID: {trackno}\nPayment: {payment_method}\nTotal Amount: \u20b9{current_total}\n\nThank you for ordering with us!"
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
print("Order Success")


def calculation(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admins only.")
        return redirect('home')

    # --- Date Filter ---
    filter_type = request.GET.get('filter', 'today')
    now = timezone.now()

    if filter_type == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        label = 'Today'
    elif filter_type == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        label = 'This Week'
    elif filter_type == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        label = 'This Month'
    elif filter_type == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        label = 'This Year'
    elif filter_type == 'custom':
        try:
            start_date = timezone.make_aware(datetime.strptime(request.GET.get('start_date', ''), '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(request.GET.get('end_date', ''), '%Y-%m-%d')).replace(hour=23, minute=59, second=59)
            label = f"{request.GET.get('start_date')} to {request.GET.get('end_date')}"
        except (ValueError, TypeError):
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            label = 'Today (Invalid range)'
    else:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
        label = 'Today'

    # --- Query Orders in Range ---
    orders_in_range = Order.objects.filter(date_order__gte=start_date, date_order__lte=end_date)

    total_orders = orders_in_range.count()
    delivered_orders = orders_in_range.filter(order_sts='Delivered')
    cancelled_orders = orders_in_range.filter(order_sts='Cancelled')
    pending_orders = orders_in_range.exclude(order_sts__in=['Delivered', 'Cancelled'])

    total_revenue = delivered_orders.aggregate(total=Sum('price'))['total'] or 0
    cancelled_revenue = cancelled_orders.aggregate(total=Sum('price'))['total'] or 0

    # --- All-time stats ---
    all_orders = Order.objects.all()
    all_delivered = Order.objects.filter(order_sts='Delivered')
    all_revenue = all_delivered.aggregate(total=Sum('price'))['total'] or 0

    context = {
        'filter_type': filter_type,
        'label': label,
        'total_orders': total_orders,
        'delivered_count': delivered_orders.count(),
        'cancelled_count': cancelled_orders.count(),
        'pending_count': pending_orders.count(),
        'total_revenue': total_revenue,
        'cancelled_revenue': cancelled_revenue,
        'all_revenue': all_revenue,
        'all_time_orders': all_orders.count(),
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
        'recent_delivered': delivered_orders.select_related('orderitem', 'customer').order_by('-date_order')[:10],
    }
    return render(request, 'menu/calculation.html', context)


# ------------------------ PROFILE PASSWORD RESET VIA OTP ------------------------

@method_decorator(signin_required, name='dispatch')
class ProfilePasswordOTPRequestView(View):
    """Step 1: Send OTP to logged-in user's email"""
    def get(self, request):
        return render(request, 'menu/profile_otp_request.html', {'email': request.user.email})

    def post(self, request):
        email = request.user.email
        if not email:
            messages.error(request, 'No email associated with your account.')
            return redirect('profile')

        otp_code = str(random.randint(100000, 999999))
        EmailOTP.objects.filter(email=email).delete()
        EmailOTP.objects.create(email=email, otp=otp_code)

        request.session['pwd_reset_email'] = email

        subject = 'LOL Cafe - Password Change OTP'
        message = (
            f'Hi {request.user.username},\n\n'
            f'Your password change OTP is: {otp_code}\n\n'
            f'This code is valid for 10 minutes.\n'
            f'If you did not request this, please ignore this email.\n\n'
            f'- LOL Cafe Team'
        )
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
            messages.success(request, f'OTP sent to {email}. Please check your inbox.')
        except Exception as e:
            print(f'OTP send failed: {e}')
            messages.error(request, 'Failed to send OTP. Please try again.')
            return render(request, 'menu/profile_otp_request.html', {'email': email})

        return redirect('profile_otp_verify')


@method_decorator(signin_required, name='dispatch')
class ProfilePasswordOTPVerifyView(View):
    """Step 2: Verify the OTP"""
    def get(self, request):
        if not request.session.get('pwd_reset_email'):
            messages.error(request, 'Session expired. Please try again.')
            return redirect('profile_pwd_otp_request')
        return render(request, 'menu/profile_otp_verify.html')

    def post(self, request):
        email = request.session.get('pwd_reset_email')
        if not email:
            messages.error(request, 'Session expired. Please try again.')
            return redirect('profile_pwd_otp_request')

        digits = [request.POST.get(f'otp_{i}', '').strip() for i in range(1, 7)]
        entered_otp = ''.join(digits)

        try:
            otp_record = EmailOTP.objects.filter(email=email).latest('created_at')
        except EmailOTP.DoesNotExist:
            messages.error(request, 'OTP not found. Please try again.')
            return redirect('profile_pwd_otp_request')

        if otp_record.is_expired():
            otp_record.delete()
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('profile_pwd_otp_request')

        if entered_otp != otp_record.otp:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'menu/profile_otp_verify.html')

        # OTP valid — allow password change
        otp_record.delete()
        request.session['pwd_otp_verified'] = True
        return redirect('profile_new_password')


@method_decorator(signin_required, name='dispatch')
class ProfileNewPasswordView(View):
    """Step 3: Set new password after OTP verified"""
    def get(self, request):
        if not request.session.get('pwd_otp_verified'):
            messages.error(request, 'Please verify OTP first.')
            return redirect('profile_pwd_otp_request')
        return render(request, 'menu/profile_new_password.html')

    def post(self, request):
        if not request.session.get('pwd_otp_verified'):
            messages.error(request, 'Please verify OTP first.')
            return redirect('profile_pwd_otp_request')

        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not new_password or len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'menu/profile_new_password.html')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'menu/profile_new_password.html')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)  # Keep user logged in

        # Cleanup session
        request.session.pop('pwd_reset_email', None)
        request.session.pop('pwd_otp_verified', None)

        messages.success(request, '✅ Password changed successfully!')
        return redirect('profile')


# ------------------------ FORGOT PASSWORD (OTP — LOGGED-OUT USERS) ------------------------

@method_decorator(never_cache, name='dispatch')
class ForgotPasswordRequestView(View):
    """Step 1: Enter registered email → receive OTP"""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, 'menu/forgot_password_request.html')

    def post(self, request):
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'menu/forgot_password_request.html')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
            return render(request, 'menu/forgot_password_request.html')

        # Generate and store OTP
        otp_code = str(random.randint(100000, 999999))
        EmailOTP.objects.filter(email=email).delete()
        EmailOTP.objects.create(email=email, otp=otp_code)
        request.session['fp_email'] = email

        # Send OTP email
        subject = 'LOL Cafe - Password Reset OTP'
        message = (
            f'Hi {user.username},\n\n'
            f'Your password reset code is: {otp_code}\n\n'
            f'This code is valid for 10 minutes.\n'
            f'If you did not request this, please ignore this email.\n\n'
            f'- LOL Cafe Team'
        )
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
            messages.success(request, f'A 6-digit code has been sent to {email}.')
        except Exception as e:
            print(f'Forgot password OTP email failed: {e}')
            messages.error(request, 'Failed to send OTP. Please try again.')
            return render(request, 'menu/forgot_password_request.html')

        return redirect('forgot_password_verify')


@method_decorator(never_cache, name='dispatch')
class ForgotPasswordOTPVerifyView(View):
    """Step 2: Enter the 6-digit OTP"""
    def get(self, request):
        email = request.session.get('fp_email')
        if not email:
            messages.error(request, 'Session expired. Please start again.')
            return redirect('forgot_password')
        return render(request, 'menu/forgot_password_otp_verify.html', {'email': email})

    def post(self, request):
        email = request.session.get('fp_email')
        if not email:
            messages.error(request, 'Session expired. Please start again.')
            return redirect('forgot_password')

        digits = [request.POST.get(f'otp_{i}', '').strip() for i in range(1, 7)]
        entered_otp = ''.join(digits)

        try:
            otp_record = EmailOTP.objects.filter(email=email).latest('created_at')
        except EmailOTP.DoesNotExist:
            messages.error(request, 'OTP not found. Please request a new one.')
            return redirect('forgot_password')

        if otp_record.is_expired():
            otp_record.delete()
            request.session.pop('fp_email', None)
            messages.error(request, 'OTP has expired. Please start again.')
            return redirect('forgot_password')

        if entered_otp != otp_record.otp:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'menu/forgot_password_otp_verify.html', {'email': email})

        # OTP is valid
        otp_record.delete()
        request.session['fp_otp_verified'] = True
        return redirect('forgot_password_new_password')


@method_decorator(never_cache, name='dispatch')
class ForgotPasswordNewPasswordView(View):
    """Step 3: Set new password"""
    def get(self, request):
        if not request.session.get('fp_otp_verified'):
            messages.error(request, 'Please verify OTP first.')
            return redirect('forgot_password')
        return render(request, 'menu/forgot_password_new_password.html')

    def post(self, request):
        if not request.session.get('fp_otp_verified'):
            messages.error(request, 'Please verify OTP first.')
            return redirect('forgot_password')

        email = request.session.get('fp_email')
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not new_password or len(new_password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'menu/forgot_password_new_password.html')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'menu/forgot_password_new_password.html')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User not found. Please start again.')
            return redirect('forgot_password')

        user.set_password(new_password)
        user.save()

        # Cleanup session
        request.session.pop('fp_email', None)
        request.session.pop('fp_otp_verified', None)

        messages.success(request, '✅ Password reset successfully! Please log in with your new password.')
        return redirect('login')
