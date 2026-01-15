from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    UserRegisterView, UserLoginView, UserLogoutView,
    HomeView, CategoryDetailView, ProductDetailView,
    AddToCartView, CartView, DeleteCartItemView,
    IncreaseQty, DecreaseQty,
    BuyNowView, UserOrdersView, CheckoutView,
    SearchView, order_success, AddReviewView, ProfileView,
    DeleteAccountView
)

urlpatterns = [

    # ---------------- AUTH ----------------
    path("", UserLoginView.as_view(), name="login"),
    path("login/", UserLoginView.as_view()),
    path("register/", UserRegisterView.as_view(), name="register"),
    path("logout/", UserLogoutView, name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),

    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='menu/password_reset_form.html',
             email_template_name='menu/password_reset_email.html',
             subject_template_name='menu/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='menu/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='menu/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='menu/password_reset_complete.html'), 
         name='password_reset_complete'),


    # ---------------- HOME ----------------
    path("home", HomeView.as_view(), name="home"),

    # ---------------- CATEGORY ----------------
    path("category/<int:pk>/", CategoryDetailView.as_view(), name="category_detail"),

    # ---------------- PRODUCT ----------------
    path("product/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),

    # ---------------- CART ----------------
    path("cart/", CartView.as_view(), name="cart"),
    path("add-to-cart/<int:pk>/", AddToCartView.as_view(), name="add_to_cart"),
    path("cart/delete/<int:pk>/", DeleteCartItemView.as_view(), name="delete_cart"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),

    # Quantity update
    path("cart/increase/<int:pk>/", IncreaseQty.as_view(), name="increase_qty"),
    path("cart/decrease/<int:pk>/", DecreaseQty.as_view(), name="decrease_qty"),

    # ---------------- BUY NOW ----------------
    path("buy/<int:pk>/", BuyNowView.as_view(), name="buy"),

    # ---------------- ORDERS ----------------
    path("my-orders/", UserOrdersView.as_view(), name="my_orders"),
    path("order-success/", order_success, name="order_success"),
    path("add-review/<int:order_id>/", AddReviewView.as_view(), name="add_review"),

    # ---------------- SEARCH ----------------
    path("search/", SearchView.as_view(), name="search"),

    # ---------------- LEGAL & INFO ----------------
    path("terms/", auth_views.TemplateView.as_view(template_name="menu/terms.html"), name="terms"),
    path("privacy/", auth_views.TemplateView.as_view(template_name="menu/privacy.html"), name="privacy"),
    path("refund/", auth_views.TemplateView.as_view(template_name="menu/refund.html"), name="refund"),
    path("about/", auth_views.TemplateView.as_view(template_name="menu/about.html"), name="about_us"),
    path("contact/", auth_views.TemplateView.as_view(template_name="menu/contact.html"), name="contact_us"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete_account"),
]


