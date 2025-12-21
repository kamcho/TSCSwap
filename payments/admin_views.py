from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import MpesaTransaction
from django.core.paginator import Paginator

@login_required
@user_passes_test(lambda u: u.is_superuser)
def view_payments(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search', '')
    
    # Start with base queryset
    payments = MpesaTransaction.objects.all().order_by('-created_at')
    
    # Apply filters
    if status_filter:
        payments = payments.filter(status=status_filter)
        
    if date_from:
        payments = payments.filter(created_at__date__gte=date_from)
        
    if date_to:
        payments = payments.filter(created_at__date__lte=date_to)
        
    if search:
        payments = payments.filter(
            Q(phone_number__icontains=search) |
            Q(account_reference__icontains=search) |
            Q(mpesa_receipt_number__icontains=search) |
            Q(merchant_request_id__icontains=search) |
            Q(checkout_request_id__icontains=search)
        )
    
    # Get summary stats
    total_payments = payments.count()
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Status counts
    status_counts = payments.values('status').annotate(count=Count('id'))
    
    # Pagination
    paginator = Paginator(payments, 25)  # Show 25 payments per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_payments': total_payments,
        'total_amount': total_amount,
        'status_counts': status_counts,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    
    return render(request, 'payments/admin_payments.html', context)
