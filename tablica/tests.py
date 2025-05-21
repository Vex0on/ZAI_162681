import tempfile
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient
from .models import Project, Task, Comment, Attachment
from rest_framework.test import force_authenticate

class ProjectAPITest(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='ownerpass')
        self.member = User.objects.create_user(username='member', password='memberpass')

        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

        self.project = Project.objects.create(
            name="Projekt startowy",
            description="Opis",
            owner=self.owner,
            is_active=True
        )
        self.project.members.add(self.owner)

    def test_get_projects_list(self):
        response = self.client.get("/api/projects/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_single_project(self):
        response = self.client.get(f"/api/projects/{self.project.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.project.name)

    def test_create_project(self):
        data = {
            "name": "Nowy projekt",
            "description": "Opis nowego projektu",
            "owner": self.owner.id,
            "members": [self.member.id],
            "is_active": True
        }
        response = self.client.post("/api/projects/", data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Nowy projekt")
        member_ids = [m['id'] for m in response.data['members']]
        self.assertIn(self.member.id, member_ids)

    def test_put_project(self):
        data = {
            "name": "Zmieniony projekt",
            "description": "Nowy opis",
            "owner": self.owner.id,
            "members": [self.owner.id, self.member.id],
            "is_active": True
        }
        response = self.client.put(f"/api/projects/{self.project.id}/", data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Zmieniony projekt")
        self.assertEqual(len(response.data['members']), 2)

    def test_patch_project(self):
        data = {
            "name": "Zmieniona nazwa PATCH",
            "members": [self.owner.id, self.member.id]
        }
        response = self.client.patch(f"/api/projects/{self.project.id}/", data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Zmieniona nazwa PATCH")
        self.assertEqual(len(response.data['members']), 2)

    def test_delete_project(self):
        response = self.client.delete(f"/api/projects/{self.project.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

class TaskActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(username='user1', password='pass')
        self.user2 = User.objects.create_user(username='user2', password='pass')
        self.client.force_authenticate(user=self.user1)

        self.project = Project.objects.create(
            name="Test project", owner=self.user1, is_active=True
        )
        self.project.members.set([self.user1, self.user2])

        Task.objects.create(
            title="Zadanie 1", project=self.project, assigned_to=self.user1,
            status="TODO", created_at=timezone.now() - timedelta(days=1)
        )
        Task.objects.create(
            title="Zadanie 2", project=self.project, assigned_to=self.user2,
            status="INPR", created_at=timezone.now()
        )
        Task.objects.create(
            title="Zadanie 3", project=self.project, assigned_to=self.user2,
            status="DONE", created_at=timezone.now() - timedelta(days=2)
        )

    def test_recent_tasks(self):
        response = self.client.get("/api/tasks/recent/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 5)

    def test_filter_by_status(self):
        response = self.client.get("/api/tasks/by-status/?status=TODO")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(task['status'] == 'TODO' for task in response.data))

    def test_filter_by_user(self):
        response = self.client.get(f"/api/tasks/by-user/?user_id={self.user2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(task['assigned_to']['id'] == self.user2.id for task in response.data))

    def test_status_summary(self):
        response = self.client.get("/api/tasks/status-summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = {item['status']: item['count'] for item in response.data}
        self.assertIn('TODO', statuses)
        self.assertIn('INPR', statuses)
        self.assertIn('DONE', statuses)

    def test_average_tasks_per_project(self):
        response = self.client.get("/api/tasks/average-per-project/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('avg', response.data)

class TaskCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(username='user', password='pass')
        self.other_user = User.objects.create_user(username='other', password='pass')

        self.client.force_authenticate(user=self.user)

        self.project = Project.objects.create(
            name="Projekt zadaniowy",
            description="Testowy projekt",
            owner=self.user,
            is_active=True
        )
        self.project.members.set([self.user, self.other_user])

        self.task = Task.objects.create(
            title="Początkowe zadanie",
            description="Opis",
            project=self.project,
            assigned_to=self.user,
            status="TODO",
            created_at=timezone.now()
        )

    def test_get_task_list(self):
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_single_task(self):
        response = self.client.get(f"/api/tasks/{self.task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.task.title)

    def test_create_task(self):
        data = {
            "title": "Nowe zadanie",
            "description": "Opis nowego zadania",
            "project": self.project.id,
            "assigned_to": self.other_user.id,
            "status": "INPR"
        }
        response = self.client.post("/api/tasks/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Nowe zadanie")
        self.assertEqual(response.data["assigned_to"]["id"], self.other_user.id)

    def test_put_task(self):
        data = {
            "title": "Zaktualizowane zadanie",
            "description": "Nowy opis",
            "project": self.project.id,
            "assigned_to": self.user.id,
            "status": "DONE"
        }
        response = self.client.put(f"/api/tasks/{self.task.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "DONE")
        self.assertEqual(response.data["title"], "Zaktualizowane zadanie")

    def test_patch_task(self):
        data = {
            "status": "INPR"
        }
        response = self.client.patch(f"/api/tasks/{self.task.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "INPR")

    def test_delete_task(self):
        response = self.client.delete(f"/api/tasks/{self.task.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

class CommentCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(username='user', password='pass')
        self.other_user = User.objects.create_user(username='other', password='pass')
        self.client.force_authenticate(user=self.user)

        self.project = Project.objects.create(
            name="Projekt z komentarzami",
            description="Testowy projekt",
            owner=self.user,
            is_active=True
        )
        self.project.members.set([self.user, self.other_user])

        self.task = Task.objects.create(
            title="Zadanie z komentarzami",
            description="Opis",
            project=self.project,
            assigned_to=self.user,
            status="TODO",
            created_at=timezone.now()
        )

        self.comment = Comment.objects.create(
            task=self.task,
            author=self.user,
            content="Początkowy komentarz"
        )

    def test_get_comment_list(self):
        response = self.client.get("/api/comments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_single_comment(self):
        response = self.client.get(f"/api/comments/{self.comment.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], self.comment.content)

    def test_create_comment(self):
        data = {
            "task": self.task.id,
            "author": self.user.id,
            "content": "Nowy komentarz"
        }
        response = self.client.post("/api/comments/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "Nowy komentarz")

    def test_put_comment(self):
        data = {
            "task": self.task.id,
            "author": self.user.id,
            "content": "Zmieniony komentarz"
        }
        response = self.client.put(f"/api/comments/{self.comment.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Zmieniony komentarz")

    def test_patch_comment(self):
        data = {
            "content": "Treść zmieniona PATCH-em"
        }
        response = self.client.patch(f"/api/comments/{self.comment.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "Treść zmieniona PATCH-em")

    def test_delete_comment(self):
        response = self.client.delete(f"/api/comments/{self.comment.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())

class AttachmentCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user', password='pass')
        self.client.force_authenticate(user=self.user)

        self.project = Project.objects.create(
            name="Projekt z załącznikiem",
            owner=self.user,
            is_active=True
        )

        self.task = Task.objects.create(
            title="Zadanie z plikiem",
            description="Opis zadania",
            project=self.project,
            assigned_to=self.user,
            status="TODO",
            created_at=timezone.now()
        )

        self.test_file = SimpleUploadedFile(
            "test.txt", b"testowa zawartosc", content_type="text/plain"
        )

        self.attachment = Attachment.objects.create(
            task=self.task,
            file=self.test_file,
        )

    def test_get_attachment_list(self):
        response = self.client.get("/api/attachments/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_single_attachment(self):
        response = self.client.get(f"/api/attachments/{self.attachment.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['file'].endswith(".txt"))  # ✅

    def test_create_attachment(self):
        with tempfile.NamedTemporaryFile(suffix=".txt") as temp:
            temp.write(b"Zawartosc pliku")
            temp.seek(0)

            uploaded = SimpleUploadedFile(temp.name, temp.read(), content_type="text/plain")
            data = {
                "task": self.task.id,
                "file": uploaded
            }

            response = self.client.post("/api/attachments/", data, format="multipart")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("file", response.data)

    def test_patch_attachment_metadata(self):
        data = {
            "task": self.task.id
        }
        response = self.client.patch(f"/api/attachments/{self.attachment.id}/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task"], self.task.id)

    def test_delete_attachment(self):
        response = self.client.delete(f"/api/attachments/{self.attachment.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Attachment.objects.filter(id=self.attachment.id).exists())