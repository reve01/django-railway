from django.contrib import admin
from .models import Owner, Pet, Appointment, Comment, Notification


# Register your models here.
admin.site.register(Owner)
admin.site.register(Pet)
admin.site.register(Appointment)
admin.site.register(Comment)

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at')  # Las columnas a mostrar en la lista
    list_filter = ('created_at', 'user')  # Filtros útiles para encontrar las notificaciones rápidamente
    search_fields = ('user__username', 'message')  # Hacer que sea posible buscar por usuario y mensaje

admin.site.register(Notification, NotificationAdmin)