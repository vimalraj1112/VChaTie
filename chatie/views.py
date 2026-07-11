from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Conversation, Profile
from django.contrib.auth.models import User
from django.contrib import messages as django_message


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
    conversations = request.user.conversations.all()

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
def room(request, room_name):
    conversation = Conversation.objects.get(id=room_name)
    messages = conversation.message.all()

    conversation.message.exclude(sender=request.user).update(is_read=True)

    if conversation.is_group:
        display_name = conversation.group_name
        other_user = None
        other_online = False
    else:
        other_user = conversation.participants.exclude(id=request.user.id).first()
        display_name = other_user.username if other_user else 'Unknown'
        try:
            other_online = other_user.profile.is_online
        except Profile.DoesNotExist:
            other_online = False

    return render(request, 'chatie/room.html', {
        'room_name': room_name,
        'messages': messages,
        'display_name': display_name,
        'other_online': other_online,
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