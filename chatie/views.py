from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Conversation, Profile,Message
from django.contrib.auth.models import User
from django.contrib import messages as django_message
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def splash_view(request):
    return render(request, 'chatie/splash.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('inbox')
        else:
            return render(request, 'chatie/login.html', {'error': 'Invalid Credentials'})
    return render(request, 'chatie/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def inbox(request):
    conversations = request.user.conversations.exclude(deleted_for=request.user)

    conversation_data = []
    for conv in conversations:
        last_message = conv.message.last()

        if conv.is_group:
            display_name = conv.group_name
            other_user = None
        else:
            other_user = conv.participants.exclude(id=request.user.id).first()
            display_name = other_user.username if other_user else 'Unknown'

        preview = None
        if last_message:
            prefix = "You" if last_message.sender == request.user else last_message.sender.username
            preview = f"{prefix}: {last_message.text}"

        conversation_data.append({
            'conversation': conv,
            'display_name': display_name,
            'other_user': other_user,
            'preview': preview,
            'last_time': last_message.timestamp if last_message else conv.created_at,
        })

    conversation_data.sort(key=lambda x: x['last_time'], reverse=True)

    return render(request, 'chatie/inbox.html', {
        'conversation_data': conversation_data
    })


@login_required
def load_older_messages(request, room_name):
    conversation = Conversation.objects.get(id=room_name)
    before_id = request.GET.get('before')

    older = conversation.message.filter(id__lt=before_id).order_by('-timestamp')[:30]
    older = list(reversed(older))

    data = []
    for msg in older:
        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'is_sent_by_me': msg.sender_id == request.user.id,
            'text': msg.text,
            'is_deleted': msg.is_deleted,
            'image_url': msg.image.url if msg.image else None,
            'video_url': msg.video.url if msg.video else None,
            'audio_url': msg.audio.url if msg.audio else None,
            'time': msg.timestamp.strftime('%I:%M %p'),
            'is_read': msg.is_read,
        })

    return JsonResponse({'messages': data, 'has_more': len(older) == 30})
@login_required
def delete_chat(request, conversation_id):
    conversation = Conversation.objects.get(id=conversation_id)
    conversation.deleted_for.add(request.user)
    return redirect('inbox')

@login_required
def delete_message(request, message_id):
    try:
        message = Message.objects.get(id=message_id, sender=request.user)
        message.text = "This message was deleted"
        message.image = None
        message.video = None
        message.is_deleted = True
        message.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{message.conversation.id}',
            {
                'type': 'message_deleted',
                'message_id': message.id,
            }
        )
    except Message.DoesNotExist:
        pass

    return JsonResponse({'success': True})

@login_required
def leave_group(request,conversation_id):
    conversation=Conversation.objects.get(id=conversation_id)
    
    if conversation.is_group:
        conversation.participants.remove(request.user)

    return redirect('inbox')    

@login_required
def profile_settings(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']
        if 'bio' in request.POST:
            profile.bio = request.POST.get('bio', '').strip()
        profile.save()
        return redirect('profile_settings')

    return render(request, 'chatie/profile_settings.html', {
        'profile': profile
    })
@login_required
def delete_avatar(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    profile.avatar.delete(save=False)
    profile.avatar = None
    profile.save()
    return redirect('profile_settings')

@login_required
def room(request, room_name):
    conversation = Conversation.objects.get(id=room_name)

    all_messages = conversation.message.all().order_by('-timestamp')[:30]
    messages = list(reversed(all_messages))

    conversation.message.exclude(sender=request.user).update(is_read=True)

    if conversation.is_group:
        display_name = conversation.group_name
        other_user = None
        other_online = False
        other_bio = None
    else:
        other_user = conversation.participants.exclude(id=request.user.id).first()
        display_name = other_user.username if other_user else 'Unknown'
        try:
            other_online = other_user.profile.is_online
            other_bio = other_user.profile.bio
        except Profile.DoesNotExist:
            other_online = False
            other_bio = None

    return render(request, 'chatie/room.html', {
        'room_name': room_name,
        'messages': messages,
        'display_name': display_name,
        'other_online': other_online,
        'other_bio': other_bio,
        'is_group': conversation.is_group,
        'created_at': conversation.created_at,
    })


def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        if len(password) < 6:
            django_message.error(request, 'Password must be atleast 6 characters.')
            return render(request, 'chatie/register.html')

        if User.objects.filter(username=username).exists():
            django_message.error(request, 'Username already taken.')
            return render(request, 'chatie/register.html')

        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('inbox')
    return render(request, 'chatie/register.html')


@login_required
def new_conversation(request):
    users = User.objects.exclude(id=request.user.id)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('users')
        group_name = request.POST.get('group_name', '').strip()

        if len(selected_ids) == 1 and not group_name:
            other_user = User.objects.get(id=selected_ids[0])

            existing = Conversation.objects.filter(
                is_group=False,
                participants=request.user
            ).filter(
                participants=other_user
            ).first()

            if existing:
                return redirect('room', room_name=existing.id)

            conversation = Conversation.objects.create(is_group=False)
            conversation.participants.add(request.user, other_user)
            return redirect('room', room_name=conversation.id)

        conversation = Conversation.objects.create(
            is_group=True,
            group_name=group_name or "Unnamed Group"
        )
        conversation.participants.add(request.user)
        for user_id in selected_ids:
            conversation.participants.add(User.objects.get(id=user_id))

        return redirect('room', room_name=conversation.id)

    return render(request, 'chatie/new_conversation.html', {
        'users': users
    })

@login_required
def upload_media(request, room_name):
    if request.method == 'POST' and request.FILES.get('file'):
        conversation = Conversation.objects.get(id=room_name)
        uploaded_file = request.FILES['file']

        message = Message(conversation=conversation, sender=request.user)

        content_type = uploaded_file.content_type
        if content_type.startswith('image/'):
            message.image = uploaded_file
        elif content_type.startswith('video/'):
            message.video = uploaded_file
        elif content_type.startswith('audio/'):
            message.audio = uploaded_file
        else:
            return JsonResponse({'error': 'Unsupported file type'}, status=400)

        message.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{room_name}',
            {
                'type': 'chat_message',
                'message': '',
                'sender': request.user.username,
                'message_id': message.id,
                'image_url': message.image.url if message.image else None,
                'video_url': message.video.url if message.video else None,
                'audio_url': message.audio.url if message.audio else None,
            }
        )

        return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request'}, status=400)

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('inbox')
    return render(request, 'chatie/landing.html')

