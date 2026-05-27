from django.contrib import admin

from .models import ActionQueueItem, Contact, OutreachMessage, ReferralOpportunity, UserConsentEvent


admin.site.register(Contact)
admin.site.register(ReferralOpportunity)
admin.site.register(OutreachMessage)
admin.site.register(ActionQueueItem)
admin.site.register(UserConsentEvent)
