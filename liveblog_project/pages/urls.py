from django.urls import path
from .views import PageView, FAQView
from . import views


app_name = 'pages'

urlpatterns = [
    path('', views.home_page, name='home'),
    path('faq/', FAQView.as_view(), name='faq'),
    path('sitemap/', views.sitemap_page, name='sitemap_page'),
    path('<slug:slug>/', PageView.as_view(), name='page'),
    # path('dev/404/', views.custom_404_view),
    # path('dev/403/', views.custom_403_view),
]