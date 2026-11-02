from django.contrib import admin
from django.urls import include, path

from accounts.errors import handler400, handler403, handler404, handler500

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
]

handler400 = handler400
handler403 = handler403
handler404 = handler404
handler500 = handler500
