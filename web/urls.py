from django.contrib.auth.views import LogoutView
from django.urls import path

from web import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("c/<slug:slug>/", views.category_detail, name="category"),
]
