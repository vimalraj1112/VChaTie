# VChaTie 💬

A real-time, full-stack chat application built with Django, Django Channels, WebSockets, and MySQL — inspired by WhatsApp's core experience.

## Features

- **Real-time messaging** via WebSockets (Django Channels + Redis)
- **Live read receipts** — single/double/blue tick system, updating instantly
- **Typing indicators** — see when the other person is typing
- **1-on-1 and group chats**
- **Image, video, and voice messages**
- **Reply/quote messages**
- **Delete messages and chats** (with live sync across devices)
- **App-wide online/offline presence tracking**
- **Profile pictures and bio**
- **Token-based REST API** (Django REST Framework) for external clients
- **Pagination** for chat history (infinite scroll)
- **Custom UI** — branded, responsive, WhatsApp-inspired design

## Tech Stack

- **Backend**: Django 5.2, Django Channels, Daphne (ASGI server)
- **Real-time layer**: WebSockets + Redis (channel layer)
- **Database**: MySQL
- **API**: Django REST Framework with Token Authentication
- **Frontend**: HTML, CSS, vanilla JavaScript

## Architecture Highlights

- Dual authentication system: session-based for the web UI, token-based for the REST API
- Custom WebSocket consumers for chat messaging and app-wide presence tracking, kept separate for clean concerns
- Security: message-level ownership checks (only senders can delete their own messages), conversation-level participant checks (non-participants blocked from sending)
- Automated tests covering authentication, messaging, and security edge cases

## Setup

1. Clone the repo
2. Create a virtual environment and install dependencies:
```bash
   pip install -r requirements.txt
```
3. Set up Redis (or Memurai on Windows) running on `127.0.0.1:6379`
4. Copy `.env.example` to `.env` and fill in your own values
5. Run migrations:
```bash
   python manage.py migrate
```
6. Start the server:
```bash
   python manage.py runserver
```

## Running Tests

```bash
python manage.py test chatie
```

## Author

Vimal Raj — [GitHub](https://github.com/vimalraj1112)