import binascii
import struct
import tempfile
from pathlib import Path
import zlib

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# ❌ 修改前的相对导入：
# from .models import Post
# from .serializers import PostSerializer
# from .views import ...

# ✅ 修改后的绝对导入：
from blog.models import Post
from blog.serializers import PostSerializer

def png_chunk(chunk_type, data):
    checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack('>I', len(data)) + chunk_type + data + struct.pack('>I', checksum)


PNG_CONTENT = (
    b'\x89PNG\r\n\x1a\n'
    + png_chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
    + png_chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\x00'))
    + png_chunk(b'IEND', b'')
)


def make_image(name='post.png'):
    return SimpleUploadedFile(name, PNG_CONTENT, content_type='image/png')


class PostModelTests(TestCase):
    def test_post_fields_and_image_upload_path(self):
        self.assertEqual(Post._meta.get_field('author').remote_field.model, get_user_model())
        self.assertEqual(Post._meta.get_field('title').max_length, 200)
        self.assertEqual(Post._meta.get_field('text').get_internal_type(), 'TextField')
        self.assertEqual(Post._meta.get_field('image').upload_to, 'blog_image/%Y/%m/%d/')
        self.assertTrue(Post._meta.get_field('created_date').auto_now_add)
        self.assertTrue(Post._meta.get_field('published_date').null)
        self.assertTrue(Post._meta.get_field('published_date').blank)

    def test_string_representation_is_title(self):
        author = get_user_model().objects.create_user(username='author')
        post = Post.objects.create(
            author=author,
            title='A test post',
            text='Post body',
            image=make_image(),
        )

        self.assertEqual(str(post), 'A test post')
        self.assertIsNotNone(post.created_date)
        self.assertIsNone(post.published_date)


class PostSerializerTests(TestCase):
    def test_serializer_includes_all_model_fields(self):
        serializer = PostSerializer()

        self.assertEqual(
            set(serializer.fields),
            {'id', 'author', 'title', 'text', 'image', 'created_date', 'published_date'},
        )

    def test_serializer_represents_post_fields(self):
        author = get_user_model().objects.create_user(username='author')
        post = Post.objects.create(
            author=author,
            title='Serialized post',
            text='Serialized body',
            image=make_image(),
        )

        data = PostSerializer(post).data

        self.assertEqual(data['author'], author.pk)
        self.assertEqual(data['title'], post.title)
        self.assertEqual(data['text'], post.text)
        self.assertTrue(data['image'].endswith(post.image.name))
        self.assertEqual(data['published_date'], None)
        self.assertIn('created_date', data)


class BlogImagesAPITests(APITestCase):
    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=Path(self.temp_media.name))
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.temp_media.cleanup)

        self.author = get_user_model().objects.create_user(username='api-author')
        self.list_url = reverse('post-list')
        self.post = Post.objects.create(
            author=self.author,
            title='Existing post',
            text='Existing body',
            image=make_image('existing.png'),
        )

    def test_api_root_lists_post_endpoint(self):
        response = self.client.get('/api_root/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Post', response.data)

    def test_list_posts(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], self.post.title)

    def test_retrieve_post(self):
        response = self.client.get(reverse('post-detail', args=[self.post.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.post.pk)
        self.assertEqual(response.data['text'], self.post.text)

    def test_create_post_with_image_upload(self):
        response = self.client.post(
            self.list_url,
            {
                'author': self.author.pk,
                'title': 'New post',
                'text': 'New body',
                'image': make_image('new.png'),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created = Post.objects.get(pk=response.data['id'])
        self.assertEqual(created.author, self.author)
        self.assertEqual(created.title, 'New post')
        self.assertTrue(created.image.name.startswith('blog_image/'))
        self.assertTrue(created.image.name.endswith('new.png'))

    def test_patch_post(self):
        response = self.client.patch(
            reverse('post-detail', args=[self.post.pk]),
            {'title': 'Updated title'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'Updated title')
        self.assertEqual(self.post.text, 'Existing body')

    def test_put_post(self):
        response = self.client.put(
            reverse('post-detail', args=[self.post.pk]),
            {
                'author': self.author.pk,
                'title': 'Replaced post',
                'text': 'Replaced body',
                'image': make_image('replaced.png'),
                'published_date': '2026-10-09T12:00:00Z',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'Replaced post')
        self.assertEqual(self.post.text, 'Replaced body')
        self.assertIsNotNone(self.post.published_date)

    def test_delete_post(self):
        response = self.client.delete(reverse('post-detail', args=[self.post.pk]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

from rest_framework.test import APITestCase
from rest_framework import status

class BlogAPITestCase(APITestCase):
    def test_sample(self):
        """基础环境验证测试"""
        self.assertEqual(1 + 1, 2)