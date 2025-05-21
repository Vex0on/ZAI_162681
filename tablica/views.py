from django.db.models import Count, Avg
from rest_framework import viewsets, permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Project, Task, Comment, Attachment
from .serializers import ProjectSerializer, TaskSerializer, CommentSerializer, AttachmentSerializer, RegisterSerializer


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'], url_path='with-task-count')
    def with_task_count(self, request):
        projects = Project.objects.annotate(task_count=Count('tasks'))
        data = [
            {
                'id': p.id,
                'name': p.name,
                'task_count': p.task_count
            }
            for p in projects
        ]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='with-comment-count')
    def with_comment_count(self, request):
        projects = Project.objects.annotate(comment_count=Count('tasks__comments'))
        data = [
            {
                'id': p.id,
                'name': p.name,
                'comment_count': p.comment_count
            }
            for p in projects
        ]
        return Response(data)

    @action(detail=False, methods=['get'], url_path='active')
    def active_projects(self, request):
        projects = Project.objects.filter(is_active=True)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='unactive')
    def inactive_projects(self, request):
        projects = Project.objects.filter(is_active=False)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

class TaskCommentListView(ListAPIView):
    serializer_class = CommentSerializer

    def get_queryset(self):
        task_id = self.kwargs['task_id']
        return Comment.objects.filter(task_id=task_id)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    @action(detail=False, methods=['get'], url_path='recent')
    def recent_tasks(self, request):
        recent_tasks = Task.objects.order_by('-created_at')[:5]
        serializer = self.get_serializer(recent_tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-status')
    def filter_by_status(self, request):
        """
        Filtrowanie zadań po statusie.
        Możliwe wartości: TODO, INPR, DONE
        Przykład: /api/tasks/by-status/?status=TODO
        """
        status = request.query_params.get('status')
        if status:
            tasks = Task.objects.filter(status=status)
        else:
            tasks = Task.objects.all()
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-user')
    def filter_by_user(self, request):
        """
        Filtrowanie zadań po przypisanym użytkowniku.
        Możliwe wartości: 1, 2, 3...
        Przykład: /api/tasks/by-status/?user_id=1
        """
        user_id = request.query_params.get('user_id')
        if user_id:
            tasks = Task.objects.filter(assigned_to__id=user_id)
        else:
            tasks = Task.objects.none()
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='status-summary')
    def status_summary(self, request):
        summary = Task.objects.values('status').annotate(count=Count('id'))
        return Response(summary)

    @action(detail=False, methods=['get'], url_path='average-per-project')
    def average_tasks_per_project(self, request):
        summary = Project.objects.annotate(task_count=Count('tasks')).aggregate(avg=Avg('task_count'))
        return Response(summary)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get'], url_path='recent')
    def recent_comments(self, request):
        recent_comments = Comment.objects.order_by('-created_at')[:5]
        serializer = self.get_serializer(recent_comments, many=True)
        return Response(serializer.data)

class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    # permission_classes = [permissions.IsAuthenticated]
