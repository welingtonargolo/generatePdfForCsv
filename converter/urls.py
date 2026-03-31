from django.urls import path
from .views import HomeView, SettingsView, CompareView

app_name = 'converter'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('auditor/', CompareView.as_view(), name='compare'),
    path('configuracoes/', SettingsView.as_view(), name='settings'),
]
