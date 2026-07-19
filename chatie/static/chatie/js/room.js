function initChatRoom(roomName, currentUsername) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const chatSocket = new WebSocket(
        wsProtocol + window.location.host + '/ws/chat/' + roomName + '/'
);

    chatSocket.onopen = function() {
        console.log('Chat socket OPENED for room', roomName);
    };

    window.addEventListener('pagehide', function() {
        chatSocket.close();
    });

    const chatWindow = document.querySelector('#chat-window');
    let typingTimeout;

    let oldestLoadedId = null;
let isLoadingOlder = false;
let hasMoreMessages = true;

const firstBubble = chatWindow.querySelector('.message-bubble');
if (firstBubble) {
    oldestLoadedId = firstBubble.dataset.messageId;
}

chatWindow.addEventListener('scroll', function() {
    if (chatWindow.scrollTop < 50 && !isLoadingOlder && hasMoreMessages) {
        loadOlderMessages();
    }
});

function loadOlderMessages() {
    if (!oldestLoadedId) return;
    isLoadingOlder = true;

    const previousScrollHeight = chatWindow.scrollHeight;

    fetch(window.location.pathname + 'older-messages/?before=' + oldestLoadedId)
        .then(function(res) { return res.json(); })
        .then(function(data) {
            if (data.messages.length === 0) {
                hasMoreMessages = false;
                isLoadingOlder = false;
                return;
            }

            data.messages.forEach(function(msg) {
                const bubble = buildHistoryBubble(msg);
                chatWindow.insertBefore(bubble, chatWindow.firstChild);
            });

            oldestLoadedId = data.messages[0].id;
            hasMoreMessages = data.has_more;

            chatWindow.scrollTop = chatWindow.scrollHeight - previousScrollHeight;
            isLoadingOlder = false;
        });
}

function buildHistoryBubble(msg) {
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble ' + (msg.is_sent_by_me ? 'message-sent' : 'message-received');
    bubble.dataset.messageId = msg.id;

    if (!msg.is_sent_by_me) {
        const nameTag = document.createElement('div');
        nameTag.className = 'message-sender-name';
        nameTag.textContent = msg.sender;
        bubble.appendChild(nameTag);
    }

    if (msg.is_deleted) {
        const deletedText = document.createElement('div');
        deletedText.className = 'deleted-text';
        deletedText.textContent = 'This message was deleted';
        bubble.appendChild(deletedText);
    } else if (msg.image_url) {
        const link = document.createElement('a');
        link.href = msg.image_url;
        link.target = '_blank';
        link.className = 'media-link';
        const img = document.createElement('img');
        img.src = msg.image_url;
        img.className = 'media-bubble';
        link.appendChild(img);
        bubble.appendChild(link);
    } else if (msg.video_url) {
        const vid = document.createElement('video');
        vid.src = msg.video_url;
        vid.controls = true;
        vid.className = 'media-bubble';
        bubble.appendChild(vid);
    } else if (msg.audio_url) {
        const audio = document.createElement('audio');
        audio.src = msg.audio_url;
        audio.controls = true;
        audio.className = 'audio-bubble';
        bubble.appendChild(audio);
    } else {
        const textNode = document.createElement('div');
        textNode.textContent = msg.text;
        bubble.appendChild(textNode);
    }

    const meta = document.createElement('div');
    meta.className = 'msg-meta';
    const timeSpan = document.createElement('span');
    timeSpan.className = 'msg-time';
    timeSpan.textContent = msg.time;
    meta.appendChild(timeSpan);

    if (msg.is_sent_by_me) {
        const tick = document.createElement('span');
        tick.className = 'tick ' + (msg.is_read ? 'tick-blue' : 'tick-gray');
        tick.innerHTML = msg.is_read ? '&#10003;&#10003;' : '&#10003;';
        meta.appendChild(tick);
    }

    bubble.appendChild(meta);
    return bubble;
}

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function deleteMessage(messageId, el) {
        if (!confirm('Delete this message?')) return;

        fetch('/chatie/delete-message/' + messageId + '/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        }).then(function() {
            const bubble = el.closest('.message-bubble');
            bubble.innerHTML = '<div class="deleted-text">This message was deleted</div>';
        });
    }

    function addMessageToScreen(sender, text, messageId, imageUrl, videoUrl, audioUrl, replySnippet, replySender) {
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

        if (isSentByMe) {
            const deleteBtn = document.createElement('span');
            deleteBtn.className = 'delete-msg-btn';
            deleteBtn.innerHTML = '&#128465;';
            deleteBtn.onclick = function() {
                deleteMessage(messageId, deleteBtn);
            };
            bubble.appendChild(deleteBtn);
        }

        const replyBtn = document.createElement('span');
        replyBtn.className = 'reply-btn';
        replyBtn.innerHTML = '&#8617;';
        replyBtn.onclick = function() {
            setReply(messageId, sender, text);
        };
        bubble.appendChild(replyBtn);

        if (replySnippet) {
            const replyPreview = document.createElement('div');
            replyPreview.className = 'reply-preview';
            replyPreview.innerHTML = '<strong>' + replySender + '</strong><div>' + replySnippet + '</div>';
            bubble.appendChild(replyPreview);
        }

        if (imageUrl) {
            const link = document.createElement('a');
            link.href = imageUrl;
            link.target = '_blank';
            link.className = 'media-link';
            const img = document.createElement('img');
            img.src = imageUrl;
            img.className = 'media-bubble';
            link.appendChild(img);
            bubble.appendChild(link);
        } else if (videoUrl) {
            const vid = document.createElement('video');
            vid.src = videoUrl;
            vid.controls = true;
            vid.className = 'media-bubble';
            bubble.appendChild(vid);
        } else if (audioUrl) {
            const audio = document.createElement('audio');
            audio.src = audioUrl;
            audio.controls = true;
            audio.className = 'audio-bubble';
            bubble.appendChild(audio);
        } else {
            const textNode = document.createElement('div');
            textNode.textContent = text;
            bubble.appendChild(textNode);
        }

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

    function showTypingIndicator(sender) {
        let indicator = document.querySelector('#typing-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'typing-indicator';
            indicator.className = 'typing-indicator';
            chatWindow.appendChild(indicator);
        }
        indicator.textContent = sender + ' is typing...';
        chatWindow.scrollTop = chatWindow.scrollHeight;

        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(function() {
            if (indicator) indicator.remove();
        }, 2000);
    }

    chatSocket.onmessage = function(e) {
        console.log('Received from server:', e.data);
        const data = JSON.parse(e.data);

        if (data.type === 'message') {
            addMessageToScreen(data.sender, data.message, data.message_id, data.image_url, data.video_url, data.audio_url, data.reply_snippet, data.reply_sender);
        }

        if (data.type === 'read_receipt') {
            document.querySelectorAll('.message-sent .sent-tick').forEach(function(tick) {
                tick.innerHTML = '&#10003;&#10003;';
                tick.classList.remove('tick-gray');
                tick.classList.add('tick-blue');
            });
        }

        if (data.type === 'message_deleted') {
            const bubble = document.querySelector('[data-message-id="' + data.message_id + '"]');
            if (bubble) {
                bubble.innerHTML = '<div class="deleted-text">This message was deleted</div>';
            }
        }

        if (data.type === 'typing') {
            showTypingIndicator(data.sender);
        }
    };

    chatSocket.onclose = function(e) {
        console.error('Chat socket closed unexpectedly');
    };

    const messageInput = document.querySelector('#chat-message-input');
    const sendButton = document.querySelector('#chat-message-submit');

    messageInput.focus();

    messageInput.addEventListener('input', function() {
        chatSocket.send(JSON.stringify({ type: 'typing' }));
    });

    messageInput.addEventListener('keyup', function(e) {
        if (e.key === 'Enter') {
            sendButton.click();
        }
    });

    sendButton.addEventListener('click', function() {
        const message = messageInput.value.trim();
        if (message === '') return;

        const payload = { message: message };
        if (typeof currentReplyId !== 'undefined' && currentReplyId) {
            payload.reply_to = currentReplyId;
        }

        chatSocket.send(JSON.stringify(payload));
        messageInput.value = '';

        if (typeof cancelReply === 'function') cancelReply();
    });

    const fileInput = document.querySelector('#file-input');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = fileInput.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            fetch(window.location.pathname + 'upload/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: formData
            }).then(function(res) {
                fileInput.value = '';
            });
        });
    }

    const micBtn = document.querySelector('#mic-btn');
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

    if (micBtn) {
        micBtn.addEventListener('click', function() {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        });
    }

    function startRecording() {
        navigator.mediaDevices.getUserMedia({ audio: true }).then(function(stream) {
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = function(e) {
                audioChunks.push(e.data);
            };

            mediaRecorder.onstop = function() {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                uploadAudio(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            micBtn.classList.add('recording');
        }).catch(function(err) {
            alert('Microphone access denied or unavailable.');
        });
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            micBtn.classList.remove('recording');
        }
    }

    function uploadAudio(blob) {
        const formData = new FormData();
        formData.append('file', blob, 'voice-message.webm');

        fetch(window.location.pathname + 'upload/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData
        });
    }
}