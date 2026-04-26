from django.urls import path
from .views import (
    AnalisisRendimientoView,
    ListarSolucionesView,
    ExportarDocView,
    ChatAgenteView,
)

urlpatterns = [
    path('analisis-rendimiento/', AnalisisRendimientoView.as_view(), name='analisis_rendimiento'),
    path('listar-soluciones/',    ListarSolucionesView.as_view(),    name='listar_soluciones'),
    path('exportar-doc/',         ExportarDocView.as_view(),         name='exportar_doc'),
    path('chat-agente/',          ChatAgenteView.as_view(),          name='chat_agente'),
]