from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.index, name='index'),
    path('conversation/<int:user_id>/', views.conversation, name='conversation'),
    path('search/', views.search_users, name='search_users'),
    path('conversation/delete/<int:conversation_id>/', views.delete_conversation, name='delete_conversation'),
    path('message/delete/<int:message_id>/', views.delete_message, name='delete_message'),
]