from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from graphene_file_upload.django import FileUploadGraphQLView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    ProjectViewSet, TaskViewSet, CommentViewSet, AttachmentViewSet,
    RegisterView, TaskCommentListView
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'attachments', AttachmentViewSet)

urlpatterns = [
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/', include(router.urls)),
    path('api/tasks/<int:task_id>/comments/', TaskCommentListView.as_view(), name='task-comments'),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path("graphql/", FileUploadGraphQLView.as_view(graphiql=True)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
