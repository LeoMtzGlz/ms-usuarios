from django.urls import path
from .views import (
    CustomTokenObtainPairView, 
    PrivacidadInfoView, 
    AceptarPrivacidadView
)

urlpatterns = [
    # Endpoint de Login (Usando tu nuevo serializer)
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # Endpoints de Privacidad (HU-29)
    path('privacidad/', PrivacidadInfoView.as_view(), name='privacidad-info'),
    path('privacidad/aceptar/', AceptarPrivacidadView.as_view(), name='privacidad-aceptar'),
]