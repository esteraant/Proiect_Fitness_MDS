from django.contrib import admin
from django.urls import path
from fitness_app import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('', views.home_view, name='home'),
    path('instructori/', views.instructors_view, name='instructors'),
    path('instructori/<int:instructor_id>/', views.instructor_detail_view, name='instructor_detail'),
    path('register/', views.register_view, name='register'),
    path('program/', views.classes_view, name='fitness_classes_list'),
    path('management/', views.admin_dashboard_view, name='admin_dashboard'),
    path('clasa/<int:class_id>/', views.class_detail_view, name='class_detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
