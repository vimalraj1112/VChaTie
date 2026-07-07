from django.urls import path
from . import views

urlpatterns=[
    path('login/',views.login_view,name='login'),
    path('inbox',views.inbox,name='inbox'),
    path('logout',views.logout_view,name='logout'),
    path('room/<str:room_name>/', views.room, name='room'),
    
]