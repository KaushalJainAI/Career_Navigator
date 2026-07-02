from django.urls import path

from .views import BillingSummaryView, CreditLedgerListView, ManualTopUpView, PricingView

urlpatterns = [
    path('summary/', BillingSummaryView.as_view(), name='billing-summary'),
    path('pricing/', PricingView.as_view(), name='billing-pricing'),
    path('ledger/', CreditLedgerListView.as_view(), name='billing-ledger'),
    path('top-up/', ManualTopUpView.as_view(), name='billing-top-up'),
]
