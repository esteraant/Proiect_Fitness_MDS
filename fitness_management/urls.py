from django.contrib import admin
from django.urls import path
from fitness_app import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # path('', views.home_view, name='home'),
    path('', views.index_view, name='index'), 
    path('acasa/', views.home_view, name='home'),

    path('instructori/', views.instructors_view, name='instructors'),
    path('instructori/<int:instructor_id>/', views.instructor_detail_view, name='instructor_detail'),
    path('register/', views.register_view, name='register'),
    path('program/', views.classes_view, name='fitness_classes_list'),
    path('management/', views.admin_dashboard_view, name='admin_dashboard'),
    path('clasa/<int:class_id>/', views.class_detail_view, name='class_detail'),
    path('profil/', views.profile_view, name='profile'),
    path('profil/freeze/', views.freeze_subscription, name='freeze_subscription'),
    path('rezerva/<int:class_id>/', views.book_class, name='book_class'),
    path('recenzii/', views.reviews_list_view, name='reviews_list'),
    path('recenzii/adauga/<int:class_id>/', views.add_review_view, name='add_review'),
    path('program/', views.classes_view, name='fitness_classes_list')
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
