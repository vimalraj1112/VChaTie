from django.urls import path
from . import views

urlpatterns=[
    path('', views.splash_view, name='splash'),
    path('start/', views.landing_view, name='landing'),
    path('register/',views.register_view,name='register'),
    path('login/',views.login_view,name='login'),
    path('inbox',views.inbox,name='inbox'),
    path('logout',views.logout_view,name='logout'),
    path('new',views.new_conversation,name='new_conversation'),
    path('delete-chat/<int:conversation_id>/', views.delete_chat, name='delete_chat'),
    path('room/<str:room_name>/', views.room, name='room'),
    path('room/<str:room_name>/upload/', views.upload_media, name='upload_media'),
    path('leave-group/<int:conversation_id>/', views.leave_group, name='leave_group'),
    path('delete-message/<int:message_id>/', views.delete_message, name='delete_message'),
    path('profile/', views.profile_settings, name='profile_settings'),
    path('profile/delete-photo/', views.delete_avatar, name='delete_avatar'),
    path('room/<str:room_name>/older-messages/', views.load_older_messages, name='load_older_messages'),
    
]