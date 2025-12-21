from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test
from . import views
from . import admin_views

app_name = 'payments'

urlpatterns = [
    # Payment pages
    path('subscription/', TemplateView.as_view(template_name='payments/subscription.html'), name='subscription'),
    path('pay/', views.PaymentView.as_view(), name='make_payment'),
    
    # Admin
    path('admin/payments/', 
         user_passes_test(lambda u: u.is_superuser)(admin_views.view_payments), 
         name='admin_payments'),
    
    # API Endpoints
    path('initiate-payment/', csrf_exempt(views.initiate_payment), name='initiate_payment'),
    path('mpesa-callback/', csrf_exempt(views.mpesa_callback), name='mpesa_callback'),
    path('transaction/<int:transaction_id>/', views.check_transaction_status, name='check_transaction_status'),
]
