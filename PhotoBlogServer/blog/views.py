from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import Post
from .serializers import PostSerializer


class BlogImages(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    # 추가 편의기능: 제목/내용 검색 + 최신순 정렬
    # 예) GET /api_root/Post/?search=가을
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'text']
    ordering_fields = ['created_date', 'published_date', 'title']
    ordering = ['-created_date']
