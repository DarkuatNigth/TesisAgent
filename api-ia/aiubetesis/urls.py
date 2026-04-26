# api/urls.py
from django.urls import path
from .views import AnalisisRendimientoView

urlpatterns = [
    path('analisis-rendimiento/', AnalisisRendimientoView.as_view(), name='analisis_rendimiento'),
    path('descargar-plan/<int:pk>/', DescargarPlanWordView.as_view(), name='descargar_plan_word'),
]
