function initCall(roomName, currentUsername) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const callSocket = new WebSocket(wsProtocol + window.location.host + '/ws/call/' + roomName + '/');

    let localStream = null;
    let peerConnection = null;
    let incomingOffer = null;
    let currentCallKind = 'video';

    const overlay = document.getElementById('call-overlay');
    const statusEl = document.getElementById('call-status');
    const remoteVideo = document.getElementById('remote-video');
    const localVideo = document.getElementById('local-video');
    const acceptBtn = document.getElementById('accept-call-btn');

    const rtcConfig = {
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    };

    window.startCall = function(kind) {
        currentCallKind = kind;
        overlay.style.display = 'flex';
        statusEl.textContent = 'Calling...';
        acceptBtn.style.display = 'none';

        callSocket.send(JSON.stringify({ type: 'call-request', call_kind: kind }));
    };

    window.acceptCall = async function() {
        acceptBtn.style.display = 'none';
        statusEl.textContent = 'Connecting...';
        await setupLocalMedia(currentCallKind);
        await createPeerConnection();
        await peerConnection.setRemoteDescription(incomingOffer);
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        callSocket.send(JSON.stringify({ type: 'answer', payload: answer }));
    };

    window.endCall = function() {
        callSocket.send(JSON.stringify({ type: 'hangup' }));
        cleanupCall();
    };

    function cleanupCall() {
        overlay.style.display = 'none';
        if (peerConnection) {
            peerConnection.close();
            peerConnection = null;
        }
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
        }
        remoteVideo.srcObject = null;
        localVideo.srcObject = null;
    }

    async function setupLocalMedia(kind) {
        const constraints = kind === 'video' ? { video: true, audio: true } : { video: false, audio: true };
        localStream = await navigator.mediaDevices.getUserMedia(constraints);
        localVideo.srcObject = localStream;
        localVideo.style.display = kind === 'video' ? 'block' : 'none';
    }

    async function createPeerConnection() {
        peerConnection = new RTCPeerConnection(rtcConfig);

        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });

        peerConnection.ontrack = function(event) {
            remoteVideo.srcObject = event.streams[0];
            statusEl.textContent = 'Connected';
        };

        peerConnection.onicecandidate = function(event) {
            if (event.candidate) {
                callSocket.send(JSON.stringify({ type: 'ice-candidate', payload: event.candidate }));
            }
        };
    }

    callSocket.onmessage = async function(e) {
        const data = JSON.parse(e.data);

        if (data.type === 'call-request') {
            currentCallKind = data.call_kind;
            overlay.style.display = 'flex';
            statusEl.textContent = data.sender + ' is calling (' + data.call_kind + ')...';
            acceptBtn.style.display = 'inline-block';
        }

        if (data.type === 'answer') {
            await peerConnection.setRemoteDescription(data.payload);
            statusEl.textContent = 'Connected';
        }

        if (data.type === 'ice-candidate') {
            if (peerConnection) {
                try {
                    await peerConnection.addIceCandidate(data.payload);
                } catch (err) {
                    console.error('Error adding ICE candidate', err);
                }
            }
        }

        if (data.type === 'hangup') {
            cleanupCall();
        }
    };

    
    const originalStartCall = window.startCall;
    window.startCall = async function(kind) {
        originalStartCall(kind);
        await setupLocalMedia(kind);
        await createPeerConnection();
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        incomingOffer = offer;
        callSocket.send(JSON.stringify({ type: 'offer', payload: offer, call_kind: kind }));
    };

    callSocket.addEventListener('message', function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'offer') {
            incomingOffer = data.payload;
        }
    });
}