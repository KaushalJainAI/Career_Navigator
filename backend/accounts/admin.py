from django.contrib import admin

from .models import GuestSession, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier', 'credits_remaining', 'created_at')
    list_filter = ('tier',)
    search_fields = ('user__email', 'user__username')


admin.site.register(GuestSession)
