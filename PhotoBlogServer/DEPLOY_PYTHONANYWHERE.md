# PythonAnywhere 배포 절차

이 프로젝트는 PythonAnywhere의 **Web app + Manual configuration** 방식으로 배포할 수 있다.

## 1. 콘솔에서 프로젝트 준비

```bash
git clone https://github.com/0733-Y/PhotoBlog.git
cd PhotoBlog/PhotoBlogServer
python3.10 -m venv ~/.virtualenvs/photoblog
source ~/.virtualenvs/photoblog/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

## 2. Web 탭 설정

- Web app: Manual configuration
- Virtualenv: `/home/<username>/.virtualenvs/photoblog`
- Source code: `/home/<username>/PhotoBlog/PhotoBlogServer`
- WSGI file: 해당 파일의 내용을 다음처럼 설정한다.

```python
import os
import sys

project_home = '/home/<username>/PhotoBlog/PhotoBlogServer'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

`<username>`은 PythonAnywhere 계정명으로 바꾼다.

## 3. Static / Media 매핑

Web 탭의 Static files에 다음 두 항목을 추가한다.

| URL | Directory |
|---|---|
| `/static/` | `/home/<username>/PhotoBlog/PhotoBlogServer/staticfiles` |
| `/media/` | `/home/<username>/PhotoBlog/PhotoBlogServer/media` |

그 다음 **Reload** 후 아래 주소로 확인한다.

```text
https://<username>.pythonanywhere.com/api_root/Post/
```

이 저장소의 `config/settings.py`에는 PythonAnywhere 호스트 허용과 `STATIC_ROOT`가 반영되어 있다.
