from django.urls import path

from web import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("issues/all/", views.all_issues, name="all_issues"),
    path("issues/<int:number>/", views.issue_detail, name="issue"),
    path("search/", views.search, name="search"),
]
