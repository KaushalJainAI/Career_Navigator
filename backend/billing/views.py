from collections import defaultdict

from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CreditLedger
from .pricing import CATALOG, SIGNUP_BONUS
from .serializers import CreditLedgerSerializer
from .services import balance as credit_balance


class BillingSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = CreditLedger.objects.filter(user=request.user)
        balance = credit_balance(request.user)
        spent = -(rows.filter(delta__lt=0).aggregate(t=Sum('delta'))['t'] or 0)
        earned = rows.filter(delta__gt=0).aggregate(t=Sum('delta'))['t'] or 0

        by_reason = defaultdict(int)
        for reason, delta in rows.values_list('reason', 'delta'):
            if delta < 0:
                by_reason[reason] += -delta

        return Response({
            'balance': balance,
            'currency': 'credits',
            'spent_total': spent,
            'earned_total': earned,
            'spent_by_reason': dict(by_reason),
            'latest': CreditLedgerSerializer(rows[:5], many=True).data,
            'signup_bonus': SIGNUP_BONUS,
            'pricing': CATALOG,
            # Rolling credits, no subscription to cancel — nothing to bill until
            # Stripe lands, so there is never a surprise charge.
            'stripe_enabled': False,
            'credits_never_expire': True,
        })


class PricingView(APIView):
    """Price list so the UI can show what each action costs before the user
    spends. Auth-only to keep it same-origin; reveals no user data."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'signup_bonus': SIGNUP_BONUS,
            'currency': 'credits',
            'credits_never_expire': True,
            'items': CATALOG,
        })


class CreditLedgerListView(generics.ListAPIView):
    serializer_class = CreditLedgerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CreditLedger.objects.filter(user=self.request.user)


class ManualTopUpView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = int(request.data.get('amount', 0) or 0)
        if amount <= 0 or amount > 10000:
            return Response({'detail': 'Amount must be between 1 and 10000 credits.'}, status=status.HTTP_400_BAD_REQUEST)
        row = CreditLedger.objects.create(
            user=request.user,
            delta=amount,
            reason='top_up',
            meta={'source': 'manual_dev_top_up'},
        )
        return Response(CreditLedgerSerializer(row).data, status=status.HTTP_201_CREATED)
