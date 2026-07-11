function initChatRoom(roomName, currentUsername) {
    const chatSocket = new WebSocket(
        'ws://' + window.location.host + '/ws/chat/' + roomName + '/'
    );

    window.addEventListener('pagehide', function() {
        chatSocket.close();
    });

    const chatWindow = document.querySelector('#chat-window');

    function addMessageToScreen(sender, text, messageId) {
        const bubble = document.createElement('div');
        const isSentByMe = sender === currentUsername;
        bubble.className = 'message-bubble ' + (isSentByMe ? 'message-sent' : 'message-received');
        bubble.dataset.messageId = messageId;

        if (!isSentByMe) {
            const nameTag = document.createElement('div');
            nameTag.className = 'message-sender-name';
            nameTag.textContent = sender;
            bubble.appendChild(nameTag);
        }

        const textNode = document.createElement('div');
        textNode.textContent = text;
        bubble.appendChild(textNode);

        const meta = document.createElement('div');
        meta.className = 'msg-meta';

        const timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
        meta.appendChild(timeSpan);

        if (isSentByMe) {
            const tick = document.createElement('span');
            tick.className = 'tick tick-gray sent-tick';
            tick.innerHTML = '&#10003;';
            meta.appendChild(tick);
        }

        bubble.appendChild(meta);
        chatWindow.appendChild(bubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);

        if (data.type === 'message') {
            addMessageToScreen(data.sender, data.message, data.message_id);
        }

        if (data.type === 'read_receipt') {
            document.querySelectorAll('.message-sent .sent-tick').forEach(function(tick) {
                tick.innerHTML = '&#10003;&#10003;';
                tick.classList.remove('tick-gray');
                tick.classList.add('tick-blue');
            });
        }
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };

    const messageInput = document.querySelector('#chat-message-input');
    const sendButton = document.querySelector('#chat-message-submit');

    messageInput.focus();
    messageInput.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            sendButton.click();
        }
    });

    sendButton.addEventListener('click', function() {
        const message = messageInput.value.trim();
        if (message === '') return;

        chatSocket.send(JSON.stringify({ 'message': message }));
        messageInput.value = '';
    });
}