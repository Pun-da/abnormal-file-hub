from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileViewSet
from .rag_views import semantic_search, rag_stats

router = DefaultRouter()
router.register(r'files', FileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', include('files.stats.urls')),
    # RAG semantic search endpoints
    path('search/semantic/', semantic_search, name='semantic-search'),
    path('search/rag-stats/', rag_stats, name='rag-stats'),
] 