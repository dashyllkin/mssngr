from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Max
from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import Conversation, Message


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('index')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки ниже.')
    else:
        form = UserCreationForm()

    return render(request, 'chat/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('index')
    else:
        form = AuthenticationForm()

    return render(request, 'chat/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('login')


@login_required
def index(request):
    # Получаем только активные беседы пользователя
    conversations = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    )

    # Добавляем информацию о втором участнике и последнем сообщении для каждой беседы
    conversations_with_other = []
    for conversation in conversations:
        other_user = conversation.participants.exclude(id=request.user.id).first()
        # Получаем последнее НЕ удаленное сообщение
        last_message = conversation.messages.filter(is_deleted=False).order_by('-timestamp').first()

        conversations_with_other.append({
            'conversation': conversation,
            'other_user': other_user,
            'last_message': last_message
        })

    # Сортируем беседы по времени последнего сообщения (сначала новые)
    conversations_with_other.sort(
        key=lambda x: x['last_message'].timestamp if x['last_message'] else x['conversation'].created_at,
        reverse=True
    )

    # Получаем список всех пользователей кроме текущего
    all_users = User.objects.exclude(id=request.user.id)

    return render(request, 'chat/index.html', {
        'conversations_with_other': conversations_with_other,
        'all_users': all_users
    })


@login_required
def conversation(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    # Находим активную беседу между пользователями (ИСПРАВЛЕННЫЙ ФИЛЬТР)
    conversation_obj = Conversation.objects.filter(
        participants=request.user,
        is_active=True
    ).filter(
        participants=other_user
    ).first()

    if not conversation_obj:
        conversation_obj = Conversation.objects.create()
        conversation_obj.participants.add(request.user, other_user)

    # Помечаем сообщения как прочитанные
    conversation_obj.messages.filter(sender=other_user, is_read=False).update(is_read=True)

    return render(request, 'chat/conversation.html', {
        'conversation': conversation_obj,
        'other_user': other_user,
    })


@login_required
def search_users(request):
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)
    else:
        users = User.objects.none()

    return render(request, 'chat/search_results.html', {
        'users': users,
        'query': query
    })


@login_required
def delete_conversation(request, conversation_id):
    if request.method == 'POST':
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=request.user,  # Исправлено - один фильтр
            is_active=True
        )
        conversation.soft_delete()
        messages.success(request, 'Чат удален')
        return redirect('index')

    return redirect('index')


@login_required
def delete_message(request, message_id):
    if request.method == 'POST':
        message = get_object_or_404(Message, id=message_id, sender=request.user)
        message.soft_delete()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request'})