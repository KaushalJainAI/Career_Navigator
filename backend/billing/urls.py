from django.urls import path

from .views import BillingSummaryView, CreditLedgerListView, ManualTopUpView

urlpatterns = [
    path('summary/', BillingSummaryView.as_view(), name='billing-summary'),
    path('ledger/', CreditLedgerListView.as_view(), name='billing-ledger'),
    path('top-up/', ManualTopUpView.as_view(), name='billing-top-up'),
]
