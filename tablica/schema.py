import graphene
from graphene_django import DjangoObjectType
from .models import Project, Task, Comment, Attachment
from django.contrib.auth.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class ProjectType(DjangoObjectType):
    class Meta:
        model = Project
        fields = "__all__"

class TaskType(DjangoObjectType):
    class Meta:
        model = Task
        fields = "__all__"

class CommentType(DjangoObjectType):
    class Meta:
        model = Comment
        fields = "__all__"

class AttachmentType(DjangoObjectType):
    class Meta:
        model = Attachment
        fields = "__all__"

class Query(graphene.ObjectType):
    all_projects = graphene.List(ProjectType)
    project = graphene.Field(ProjectType, id=graphene.Int())
    all_tasks = graphene.List(TaskType)
    task = graphene.Field(TaskType, id=graphene.Int())

    all_comments = graphene.List(CommentType)
    comment = graphene.Field(CommentType, id=graphene.Int())

    all_attachments = graphene.List(AttachmentType)
    attachment = graphene.Field(AttachmentType, id=graphene.Int())

    def resolve_all_projects(root, info):
        return Project.objects.select_related("owner").prefetch_related("members").all()

    def resolve_project(root, info, id):
        return Project.objects.get(pk=id)

    def resolve_all_tasks(self, info):
        return Task.objects.select_related("project", "assigned_to").all()

    def resolve_task(self, info, id):
        return Task.objects.get(pk=id)

    def resolve_all_comments(self, info):
        return Comment.objects.select_related("task", "author").all()

    def resolve_comment(self, info, id):
        return Comment.objects.get(pk=id)

    def resolve_all_attachments(self, info):
        return Attachment.objects.select_related("task").all()

    def resolve_attachment(self, info, id):
        return Attachment.objects.get(pk=id)

class CreateProject(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        description = graphene.String()
        is_active = graphene.Boolean(default_value=True)
        owner_id = graphene.Int(required=True)
        member_ids = graphene.List(graphene.Int)

    project = graphene.Field(ProjectType)

    def mutate(self, info, name, owner_id, description=None, is_active=True, member_ids=None):
        owner = User.objects.get(id=owner_id)
        project = Project.objects.create(
            name=name, description=description or "", is_active=is_active, owner=owner
        )
        if member_ids:
            members = User.objects.filter(id__in=member_ids)
            project.members.set(members)
        project.save()
        return CreateProject(project=project)


class UpdateProject(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        name = graphene.String()
        description = graphene.String()
        is_active = graphene.Boolean()
        member_ids = graphene.List(graphene.Int)

    project = graphene.Field(ProjectType)

    def mutate(self, info, id, name=None, description=None, is_active=None, member_ids=None):
        project = Project.objects.get(pk=id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if is_active is not None:
            project.is_active = is_active
        if member_ids is not None:
            members = User.objects.filter(id__in=member_ids)
            project.members.set(members)
        project.save()
        return UpdateProject(project=project)


class DeleteProject(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        try:
            project = Project.objects.get(pk=id)
            project.delete()
            return DeleteProject(ok=True)
        except Project.DoesNotExist:
            return DeleteProject(ok=False)


class CreateTask(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String()
        project_id = graphene.Int(required=True)
        assigned_to_id = graphene.Int()
        status = graphene.String()

    task = graphene.Field(TaskType)

    def mutate(self, info, title, project_id, description=None, assigned_to_id=None, status="TO_DO"):
        project = Project.objects.get(id=project_id)
        assigned_to = User.objects.get(id=assigned_to_id) if assigned_to_id else None
        task = Task.objects.create(
            title=title,
            description=description or "",
            project=project,
            assigned_to=assigned_to,
            status=status
        )
        return CreateTask(task=task)


class UpdateTask(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        title = graphene.String()
        description = graphene.String()
        status = graphene.String()
        assigned_to= graphene.Int()

    task = graphene.Field(TaskType)

    def mutate(self, info, id, title=None, description=None, status=None):
        task = Task.objects.get(pk=id)
        if title:
            task.title = title
        if description:
            task.description = description
        if status:
            task.status = status
        task.save()
        return UpdateTask(task=task)


class DeleteTask(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        Task.objects.get(pk=id).delete()
        return DeleteTask(ok=True)

class CreateComment(graphene.Mutation):
    class Arguments:
        content = graphene.String(required=True)
        task_id = graphene.Int(required=True)
        author_id = graphene.Int(required=True)

    comment = graphene.Field(CommentType)

    def mutate(self, info, content, task_id, author_id):
        task = Task.objects.get(id=task_id)
        author = User.objects.get(id=author_id)
        comment = Comment.objects.create(content=content, task=task, author=author)
        return CreateComment(comment=comment)


class DeleteComment(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        Comment.objects.get(pk=id).delete()
        return DeleteComment(ok=True)

from graphene_file_upload.scalars import Upload

class CreateAttachment(graphene.Mutation):
    class Arguments:
        task_id = graphene.Int(required=True)
        file = Upload(required=True)

    attachment = graphene.Field(AttachmentType)

    def mutate(self, info, task_id, file):
        task = Task.objects.get(id=task_id)
        attachment = Attachment.objects.create(task=task, file=file)
        return CreateAttachment(attachment=attachment)


class DeleteAttachment(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        Attachment.objects.get(pk=id).delete()
        return DeleteAttachment(ok=True)



class Mutation(graphene.ObjectType):
    create_project = CreateProject.Field()
    update_project = UpdateProject.Field()
    delete_project = DeleteProject.Field()
    create_task = CreateTask.Field()
    update_task = UpdateTask.Field()
    delete_task = DeleteTask.Field()
    create_comment = CreateComment.Field()
    delete_comment = DeleteComment.Field()
    create_attachment = CreateAttachment.Field()
    delete_attachment = DeleteAttachment.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
