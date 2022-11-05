import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from reviews.models import Category, Genre, Review, Title, User

from .mixins import ListCreateDestroyViewSet
from .permissions import IsAdminOrMe, IsAdminOrReadOnly, IsAuthorOrReadOnly
from .serializers import (
    AuthSerializer, CategorySerializer, CommentSerializer,
    GenreSerializer, GetTokenSerializer, ReadOnlyTitleSerializer,
    ReviewSerializer, TitleSerializer, UserMyselfSerializer, UserSerializer,
)
from .filters import TitlesFilter


class CategoryViewSet(ListCreateDestroyViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'


class GenreViewSet(ListCreateDestroyViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    lookup_field = 'slug'


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.all().annotate(
        Avg('reviews__score')
    ).order_by('name')
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitlesFilter

    def get_serializer_class(self):
        if self.action in ('retrieve', 'list'):
            return ReadOnlyTitleSerializer
        return TitleSerializer


class SignUpView(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = AuthSerializer(data=request.data)

        user_in_db = User.objects.filter(
            username=request.data.get('username'),
            email=request.data.get('email')
        ).exists()

        if serializer.is_valid() or user_in_db:
            user, created = User.objects.get_or_create(
                username=serializer.data.get('username'),
                email=serializer.data.get('email')
            )
            confirmation_code = uuid.uuid4()
            user.confirmation_code = make_password(confirmation_code)
            user.save()
            send_mail(
                'Your confirmation_code',
                f'Ваш confirmation_code: {confirmation_code}',
                from_email=None,
                recipient_list=(user.email,),
                fail_silently=False,
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetTokenView(APIView):

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = GetTokenSerializer(data=request.data)
        if serializer.is_valid():
            user = get_object_or_404(
                User,
                username=serializer.data.get('username')
            )
            code = serializer.data.get('confirmation_code')
            if not check_password(code, user.confirmation_code):
                return Response(
                    'Код не верный!',
                    status=status.HTTP_400_BAD_REQUEST,
                )
            refresh = RefreshToken.for_user(user)
            access = {'access': str(refresh.access_token)}
            return Response(access, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdminOrMe,)

    filter_backends = (filters.SearchFilter,)
    search_fields = ('username',)
    lookup_field = 'username'
    pagination_class = PageNumberPagination

    @action(methods=['get', 'patch'], detail=False)
    def me(self, request):
        if request.method == 'PATCH':
            partial = True
            serializer = UserMyselfSerializer(
                request.user, data=request.data, partial=partial
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(request.user, many=False)
        return Response(serializer.data)


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )
    serializer_class = ReviewSerializer

    def get_title(self):
        title_id = self.kwargs.get('title_id')
        title = get_object_or_404(Title, pk=title_id)
        return title

    def perform_create(self, serializer):
        title = self.get_title()
        serializer.save(author=self.request.user, title=title)

    def get_queryset(self):
        title = self.get_title()
        reviews_queryset = title.reviews.all()
        return reviews_queryset


class CommentViewSet(viewsets.ModelViewSet):
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )
    serializer_class = CommentSerializer

    def get_review(self):
        review_id = self.kwargs.get('review_id')
        review = get_object_or_404(Review, pk=review_id)
        return review

    def perform_create(self, serializer):
        review = self.get_review()
        serializer.save(author=self.request.user, review=review)

    def get_queryset(self):
        review = self.get_review()
        comments_queryset = review.comments.all()
        return comments_queryset
