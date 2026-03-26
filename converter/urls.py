from django.urls import path
from .views import HomeView, SettingsView

app_name = 'converter'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('configuracoes/', SettingsView.as_view(), name='settings'),
]
