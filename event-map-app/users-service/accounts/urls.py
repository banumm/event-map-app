from django.urls import path
from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("auth/register", views.register, name="register"),
    path("auth/login", views.login_view, name="login"),
    path("users/<int:user_id>", views.get_user, name="get_user"),
]
