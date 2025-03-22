from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import TokenAuthentication

class CustomAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        open_endpoints = ["/api/register/", "/api/login/"] 

        if request.path in open_endpoints:
            return  

        auth = TokenAuthentication()
        user, auth_token = auth.authenticate(request) or (AnonymousUser(), None)
        request.user = user  
        
        if user.is_anonymous:
            return JsonResponse({"detail": "Authentication required"}, status=401)
