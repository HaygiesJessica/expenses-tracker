from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('expenses.urls')),
]
