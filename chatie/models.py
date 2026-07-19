from django.db import models
from django.contrib.auth.models import User
from decouple import config

if config('CLOUDINARY_CLOUD_NAME', default=''):
    from cloudinary_storage.storage import VideoMediaCloudinaryStorage
    media_storage = VideoMediaCloudinaryStorage()
else:
    media_storage = None

class Profile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    avatar=models.ImageField(upload_to='avatars/',blank=True,null=True)
    bio=models.CharField(max_length=200,blank=True)
    is_online=models.BooleanField(default=False)
    last_seen=models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username
    
class Conversation(models.Model):
    participants=models.ManyToManyField(User,related_name='conversations')
    is_group=models.BooleanField(default=False)
    group_name=models.CharField(max_length=200,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    deleted_for=models.ManyToManyField(User,related_name='deleted_conversations',blank=True)

    def __str__(self):
        if self.is_group:
            return self.group_name
        return f"conversations {self.id}"
    
class Message(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='message')
    sender=models.ForeignKey(User,on_delete=models.CASCADE)
    text=models.TextField(blank=True)    
    image=models.ImageField(upload_to='chat_images/',blank=True,null=True)
    video=models.FileField(upload_to='chat_videos',blank=True,null=True,storage=media_storage)
    audio=models.FileField(upload_to='chat_audio',blank=True,null=True,storage=media_storage)
    timestamp=models.DateTimeField(auto_now_add=True)
    is_read=models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    reply_to=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='replies')

    class Meta:
        ordering=['timestamp']

    def __str__(self):
        return f"{self.sender.username}:{self.text[:20]}"    

       
