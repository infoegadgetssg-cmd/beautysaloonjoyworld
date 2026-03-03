# shop/urls.py
from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.shop_view, name='shop'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('cart/update/', views.update_cart_quantity_view, name='update_cart_quantity'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success_view, name='order_success'),
    path('orders/', views.order_history_view, name='order_history'),
    path('search-suggestions/', views.search_suggestions_view, name='search_suggestions'),
    # Paystack URLs
    path('initiate-payment/<int:order_id>/', views.initiate_payment, name='initiate_payment'),
    path('verify-payment/<int:order_id>/', views.verify_payment, name='verify_payment'),
    path('paystack-webhook/', views.paystack_webhook, name='paystack_webhook'),
    # PayPal URLs
    path('paypal/pay/<int:order_id>/', views.initiate_paypal_payment, name='initiate_paypal_payment'),
    path('paypal/success/<int:order_id>/', views.paypal_success, name='paypal_success'),
    path('paypal/cancel/<int:order_id>/', views.paypal_cancel, name='paypal_cancel'),
]