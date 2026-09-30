/**
 * Reconnecting WebSocket client for GamingHub Lobby Management.
 * Manages player slot synchronization, ready states, chat, and host start triggers.
 */
class LobbyWebSocketClient {
    constructor(roomCode, currentUsername) {
        this.roomCode = roomCode.toUpperCase();
        this.currentUsername = currentUsername;
        this.socket = null;
        this.reconnectInterval = 3000;
        this.maxReconnectAttempts = 10;
        this.reconnectAttempts = 0;
        this.isHost = false;
        this.canStart = false;

        this.init();
    }

    init() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = `${wsProtocol}${window.location.host}/ws/room/${this.roomCode}/`;

        console.log(`[LobbyWS] Connecting to ${wsUrl}...`);
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = (e) => this.onOpen(e);
        this.socket.onmessage = (e) => this.onMessage(e);
        this.socket.onclose = (e) => this.onClose(e);
        this.socket.onerror = (e) => this.onError(e);
    }

    onOpen(e) {
        console.log('[LobbyWS] Connected to Room WebSocket');
        this.reconnectAttempts = 0;
        this.updateStatusIndicator('Connected', 'emerald');
    }

    onMessage(e) {
        try {
            const data = JSON.parse(e.data);
            console.log('[LobbyWS] Received:', data);

            const type = data.type || data.event;

            if (type === 'player_joined_event' || type === 'player_left_event' || type === 'player_ready_event') {
                if (data.lobby_state) {
                    this.renderLobbyState(data.lobby_state);
                }
            } else if (type === 'host_start_game_event') {
                this.handleGameStarted(data);
            } else if (type === 'chat_message_event') {
                this.appendChatMessage(data.sender, data.message);
            } else if (type === 'error') {
                alert(data.message || 'Error occurred');
            }
        } catch (err) {
            console.error('[LobbyWS] JSON parse error:', err);
        }
    }

    onClose(e) {
        console.warn(`[LobbyWS] Closed (code ${e.code}). Attempting reconnect...`);
        this.updateStatusIndicator('Disconnected', 'rose');
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.init(), this.reconnectInterval);
        }
    }

    onError(err) {
        console.error('[LobbyWS] Error:', err);
    }

    sendReadyToggle() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ event: 'player_ready' }));
        }
    }

    sendHostStartGame() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ event: 'host_start_game' }));
        }
    }

    sendChatMessage(message) {
        if (message && this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                event: 'chat_message',
                message: message
            }));
        }
    }

    renderLobbyState(state) {
        if (!state || !state.slots) return;

        const slotsContainer = document.getElementById('slots-container');
        if (!slotsContainer) return;

        slotsContainer.innerHTML = '';
        this.canStart = state.can_start;

        let currentUserIsHost = false;

        state.slots.forEach(slot => {
            const slotCard = document.createElement('div');
            slotCard.className = `p-5 rounded-2xl border transition shadow-sm ${
                slot.occupied 
                    ? 'bg-slate-900 border-slate-700/80' 
                    : 'bg-slate-950/60 border-slate-800 border-dashed'
            }`;

            if (slot.occupied) {
                if (slot.name === this.currentUsername && slot.is_host) {
                    currentUserIsHost = true;
                }

                slotCard.innerHTML = `
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <div class="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-bold flex items-center justify-center text-sm">
                                Slot ${slot.slot_index + 1}
                            </div>
                            <div>
                                <div class="flex items-center space-x-2">
                                    <h4 class="text-sm font-bold text-white">${this.escapeHtml(slot.name)}</h4>
                                    ${slot.is_host ? '<span class="px-1.5 py-0.5 text-[9px] font-extrabold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded">HOST</span>' : ''}
                                </div>
                                <span class="text-[11px] font-semibold ${slot.is_ready ? 'text-emerald-400' : 'text-amber-400'}">
                                    ${slot.is_ready ? 'READY TO PLAY' : 'NOT READY'}
                                </span>
                            </div>
                        </div>
                        <div class="w-3 h-3 rounded-full ${slot.is_ready ? 'bg-emerald-400 shadow-lg shadow-emerald-400/50' : 'bg-amber-400 shadow-lg shadow-amber-400/50'}"></div>
                    </div>
                `;
            } else {
                slotCard.innerHTML = `
                    <div class="flex items-center justify-between opacity-60">
                        <div class="flex items-center space-x-3">
                            <div class="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 text-slate-600 font-bold flex items-center justify-center text-xs">
                                Slot ${slot.slot_index + 1}
                            </div>
                            <div>
                                <h4 class="text-xs font-semibold text-slate-500">Open Slot</h4>
                                <span class="text-[10px] text-slate-600">Waiting for player...</span>
                            </div>
                        </div>
                        <i class="fa-solid fa-user-plus text-slate-700"></i>
                    </div>
                `;
            }

            slotsContainer.appendChild(slotCard);
        });

        this.isHost = currentUserIsHost;
        this.updateControlsUI(state);
    }

    updateControlsUI(state) {
        const startBtn = document.getElementById('start-game-btn');
        const readyBtn = document.getElementById('toggle-ready-btn');
        const readyStatusText = document.getElementById('ready-status-text');

        if (startBtn) {
            if (this.isHost) {
                startBtn.classList.remove('hidden');
                if (state.can_start) {
                    startBtn.disabled = false;
                    startBtn.className = "w-full py-3.5 px-6 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-extrabold text-sm rounded-2xl shadow-xl shadow-indigo-600/30 transition transform active:scale-95 cursor-pointer";
                } else {
                    startBtn.disabled = true;
                    startBtn.className = "w-full py-3.5 px-6 bg-slate-800 text-slate-500 font-bold text-sm rounded-2xl cursor-not-allowed opacity-60";
                }
            } else {
                startBtn.classList.add('hidden');
            }
        }
    }

    handleGameStarted(data) {
        console.log('[LobbyWS] Game started!', data);
        const banner = document.getElementById('game-start-banner');
        if (banner) {
            banner.classList.remove('hidden');
        }
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    }

    appendChatMessage(sender, message) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = "p-2 bg-slate-950/80 rounded-lg border border-slate-800 text-xs";
        msgDiv.innerHTML = `<strong class="text-indigo-400">${this.escapeHtml(sender)}:</strong> ${this.escapeHtml(message)}`;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
    }

    updateStatusIndicator(text, color) {
        const el = document.getElementById('ws-status-badge');
        if (el) {
            el.innerText = text;
            el.className = `text-xs font-semibold px-2.5 py-1 rounded-full bg-${color}-500/10 text-${color}-400 border border-${color}-500/20`;
        }
    }

    escapeHtml(str) {
        return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
}

// Share / Copy Link Helper
function copyRoomLink(roomCode) {
    const shareUrl = `${window.location.origin}/rooms/join/?code=${roomCode}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
        const copyText = document.getElementById('copy-text');
        if (copyText) {
            copyText.innerText = "Link Copied!";
            setTimeout(() => { copyText.innerText = "Copy Invite Link"; }, 2000);
        }
    });
}
