from django.contrib import admin

from .models import Portal, PortalAccount, PortalScrapeRun


@admin.register(Portal)
class PortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'enabled')


@admin.register(PortalAccount)
class PortalAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'portal', 'status', 'last_used_at')
    # Never surface the encrypted session blob in the admin.
    exclude = ('storage_state_ciphertext',)
    readonly_fields = ('status', 'last_used_at')


@admin.register(PortalScrapeRun)
class PortalScrapeRunAdmin(admin.ModelAdmin):
    list_display = ('user', 'portal', 'status', 'started_at', 'finished_at')
    list_filter = ('status', 'portal')
