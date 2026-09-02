import json

from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import User


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"status": "ok", "service": "users-service"})


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    """Регистрация нового пользователя с указанием роли (user / organizer)."""
    data = json.loads(request.body or "{}")

    required_fields = ["username", "password", "role"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return JsonResponse({"error": f"Missing fields: {missing}"}, status=400)

    if User.objects.filter(username=data["username"]).exists():
        return JsonResponse({"error": "Username already taken"}, status=400)

    user = User.objects.create_user(
        username=data["username"],
        password=data["password"],
        role=data["role"],
    )
    return JsonResponse({"id": user.id, "username": user.username, "role": user.role}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    data = json.loads(request.body or "{}")
    user = authenticate(request, username=data.get("username"), password=data.get("password"))
    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    login(request, user)
    return JsonResponse({"id": user.id, "username": user.username, "role": user.role})


@require_http_methods(["GET"])
def get_user(request, user_id):
    """
    Используется другими сервисами (Events Service, Attendance Service)
    для проверки существования и роли пользователя.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    return JsonResponse({"id": user.id, "username": user.username, "role": user.role})
