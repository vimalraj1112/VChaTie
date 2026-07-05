from django.db import models
from django.contrib.auth.models import User

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

    def __str__(self):
        if self.is_group:
            return self.group_name
        return f"conversations {self.id}"
    
class Message(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='message')
    sender=models.ForeignKey(User,on_delete=models.CASCADE)
    text=models.TextField(blank=True)    
    image=models.ImageField(upload_to='chat_images/',blank=True,null=True)
    timestamp=models.DateTimeField(auto_now_add=True)
    is_read=models.BooleanField(default=False)

    class Meta:
        ordering=['timestamp']

    def __str__(self):
        return f"{self.sender.username}:{self.text[:20]}"    

       
