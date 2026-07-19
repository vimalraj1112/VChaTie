function initPresence() {
    console.log('initPresence() called');

    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const presenceSocket = new WebSocket(wsProtocol + window.location.host + '/ws/presence/');

    presenceSocket.onopen = function() {
        console.log('Presence socket OPENED successfully');
    };

    presenceSocket.onerror = function(e) {
        console.log('Presence socket ERROR:', e);
    };

    presenceSocket.onclose = function(e) {
        console.log('Presence socket CLOSED. Code:', e.code, 'Reason:', e.reason);
    };

    window.addEventListener('pagehide', function() {
        presenceSocket.close();
    });
}