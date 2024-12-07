from . import views
from django.urls import path, register_converter
from .utilities import DateConverter

register_converter(DateConverter, 'date')

urlpatterns= [
    path('', views.inicio, name='inicio'),
    path('galeria', views.galeria,name="galeria"),
    path('services', views.services, name="services"),
    path('login', views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path('register', views.register, name="register"),
    path('changepassword', views.change_password, name="changepassword"),    
    path('profile',views.profile, name="profile"),
    path('booking', views.booking, name="booking"),
    path('appointment/<int:id>', views.appointment, name="appointment"),
    path('schedule/<date:start>/<str:move>', views.schedule, name="schedule"),
    path('mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
]
