// room_ws.js - WebSocket client manager for GamingHub
let socket = null;
let currentRoomData = null;
let clientSeatIndex = -1;

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let wsUrl = `${protocol}//${window.location.host}/ws/room/${ROOM_CODE}/`;
    
    if (RECONNECT_TOKEN) {
        wsUrl += `?reconnect_token=${RECONNECT_TOKEN}`;
    }

    socket = new WebSocket(wsUrl);

    socket.onopen = function() {
        console.log('WebSocket connection established.');
        const statusBadge = document.getElementById('wsStatusBadge');
        statusBadge.className = 'flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium';
        statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400"></span><span>Connected</span>';
    };

    socket.onmessage = function(event) {
        const message = JSON.parse(event.data);
        handleServerMessage(message);
    };

    socket.onclose = function(e) {
        console.warn('WebSocket connection closed. Attempting reconnect in 3s...', e);
        const statusBadge = document.getElementById('wsStatusBadge');
        statusBadge.className = 'flex items-center space-x-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-medium';
        statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span><span>Reconnecting...</span>';
        setTimeout(initWebSocket, 3000);
    };

    socket.onerror = function(err) {
        console.error('WebSocket error:', err);
    };
}

function handleServerMessage(message) {
    if (message.type === 'error') {
        showError(message.message);
    } else if (message.type === 'reaction' && message.emoji) {
        if (typeof showReactionAnimation === 'function') {
            showReactionAnimation(message.emoji);
        }
    } else if (message.type === 'room_state') {
        currentRoomData = message.data;
        if (message.data.reconnect_token) {
            RECONNECT_TOKEN = message.data.reconnect_token;
            localStorage.setItem(`reconnect_token_${ROOM_CODE}`, RECONNECT_TOKEN);
        }
        if (message.data.client_seat_index !== undefined) {
            clientSeatIndex = message.data.client_seat_index;
        }
        updateUI(message.data);
    }
}

function updateUI(data) {
    const lobbyView = document.getElementById('lobbyView');
    const gameView = document.getElementById('gameView');

    if (data.status === 'LOBBY') {
        lobbyView.classList.remove('hidden');
        gameView.classList.add('hidden');
        renderLobby(data);
    } else if (data.status === 'PLAYING' || data.status === 'FINISHED') {
        lobbyView.classList.add('hidden');
        gameView.classList.remove('hidden');
        renderGame(data);
    }
}

function renderLobby(data) {
    const grid = document.getElementById('playerSeatsGrid');
    grid.innerHTML = '';

    const isHost = data.players.some(p => p.is_host && p.reconnect_token === RECONNECT_TOKEN);
    const hostBadge = document.getElementById('hostBadge');
    const hostControls = document.getElementById('hostControls');
    const toggleReadyBtn = document.getElementById('toggleReadyBtn');
    const myPlayer = data.players.find(p => p.reconnect_token === RECONNECT_TOKEN);

    if (myPlayer) {
        toggleReadyBtn.innerText = myPlayer.is_ready ? '✓ Ready (Click to Unready)' : '⏳ Set Ready';
        toggleReadyBtn.className = myPlayer.is_ready 
            ? 'bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 px-6 rounded-xl shadow-lg transition'
            : 'bg-amber-600 hover:bg-amber-500 text-white font-semibold py-2.5 px-6 rounded-xl shadow-lg transition';
    }

    const startBtn = document.getElementById('startGameBtn');
    const reqCount = (data.game_type === 'CHESS_STANDARD') ? 2 : ((data.game_type === 'CHESS_4WAY' || data.game_type === 'CHESS_BUGHOUSE') ? 4 : 2);
    const allReady = data.players.length >= reqCount && data.players.every(p => p.is_ready);

    if (isHost) {
        hostBadge.classList.remove('hidden');
        hostControls.classList.remove('hidden');
        if (startBtn) {
            startBtn.disabled = !allReady;
            startBtn.className = allReady
                ? "bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold py-2.5 px-8 rounded-xl shadow-lg shadow-indigo-600/30 transition cursor-pointer"
                : "bg-slate-800 text-slate-500 border border-slate-700 font-bold py-2.5 px-8 rounded-xl cursor-not-allowed opacity-60";
            startBtn.innerText = allReady ? "🚀 Start Game" : `Waiting for Ready (${data.players.length}/${data.max_players})`;
        }
    } else {
        hostBadge.classList.add('hidden');
        hostControls.classList.remove('hidden');
        if (startBtn) {
            startBtn.disabled = true;
            startBtn.className = "bg-slate-800 text-slate-400 border border-slate-700 font-semibold py-2.5 px-6 rounded-xl cursor-not-allowed opacity-80";
            startBtn.innerText = "⏳ Waiting for host to start game...";
        }
    }

    for (let i = 0; i < data.max_players; i++) {
        const player = data.players.find(p => p.seat_index === i);
        const card = document.createElement('div');
        card.className = 'glass-panel p-4 rounded-xl border border-slate-700 flex flex-col justify-between space-y-3';

        if (player) {
            const isMe = (player.reconnect_token === RECONNECT_TOKEN);
            card.innerHTML = `
                <div class="flex justify-between items-start">
                    <span class="text-xs font-bold text-slate-400">Seat #${i + 1}</span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider text-white" style="background-color: ${getColorHex(player.color)}">
                        ${player.color}
                    </span>
                </div>
                <div>
                    <div class="font-bold text-white flex items-center space-x-1">
                        <span>${player.player_name}</span>
                        ${isMe ? '<span class="text-xs text-indigo-400 font-normal">(You)</span>' : ''}
                        ${player.is_host ? '<span>👑</span>' : ''}
                    </div>
                    <div class="text-xs ${player.is_connected ? 'text-emerald-400' : 'text-amber-400'} mt-0.5">
                        ${player.is_connected ? '● Online' : '⏱ Disconnected'}
                    </div>
                </div>
                <div class="flex items-center justify-between pt-2 border-t border-slate-800">
                    <span class="text-xs font-semibold ${player.is_ready ? 'text-emerald-400' : 'text-amber-400'}">
                        ${player.is_ready ? '✓ Ready' : '⏳ Not Ready'}
                    </span>
                    ${isHost && !isMe ? `<button onclick="sendKickPlayer(${i})" class="text-xs text-red-400 hover:text-red-300">Kick</button>` : ''}
                </div>
            `;
        } else {
            card.innerHTML = `
                <div class="text-xs font-bold text-slate-500">Seat #${i + 1}</div>
                <div class="text-sm font-medium text-slate-600 italic">Empty Seat</div>
                <button onclick="sendSelectSeat(${i})" class="w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-semibold rounded-lg transition">
                    Take Seat
                </button>
            `;
        }

        grid.appendChild(card);
    }
}


function renderGame(data) {
    const turnBanner = document.getElementById('turnBanner');
    const turnStatusText = document.getElementById('turnStatusText');
    const lastActionText = document.getElementById('lastActionText');
    const currentTurnColorIndicator = document.getElementById('currentTurnColorIndicator');

    const state = data.state_data;
    const gameType = data.game_type;

    if (state) {
        lastActionText.innerText = state.last_action_text || '';
        
        let turnColor = 'red';
        if (gameType === 'LUDO') {
            const currentP = state.players[state.current_player_index];
            turnColor = currentP ? currentP.color : 'red';
            const isMyTurn = (state.current_player_index === clientSeatIndex);
            turnStatusText.innerText = isMyTurn ? `Your Turn! (${currentP.name})` : `Turn: ${currentP.name}`;
            
            // Show Ludo controls
            document.getElementById('ludoControls').classList.remove('hidden');
            document.getElementById('bughouseReservePanel').classList.add('hidden');

            const rollBtn = document.getElementById('rollDiceBtn');
            const canRoll = data.client_valid_moves && data.client_valid_moves.can_roll;
            rollBtn.disabled = !canRoll;
            rollBtn.className = canRoll 
                ? "w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow-lg transition cursor-pointer"
                : "w-full py-3 bg-slate-800 text-slate-500 font-bold rounded-xl cursor-not-allowed";

            if (state.dice_value !== null && state.dice_value !== undefined) {
                document.getElementById('diceDisplay').classList.remove('hidden');
                document.getElementById('diceValueText').innerText = state.dice_value;
            } else {
                document.getElementById('diceDisplay').classList.add('hidden');
            }

            renderLudoBoard(state, data.client_valid_moves);

        } else if (gameType.startsWith('CHESS')) {
            document.getElementById('ludoControls').classList.add('hidden');

            if (gameType === 'CHESS_STANDARD') {
                turnColor = state.current_turn === 'w' ? 'white' : 'black';
                const currentP = state.players[state.current_player_index];
                const isMyTurn = (state.current_player_index === clientSeatIndex);
                turnStatusText.innerText = isMyTurn ? `Your Turn! (${currentP ? currentP.name : 'Player'})` : `Turn: ${currentP ? currentP.name : 'Player'}`;

                const isBlack = (clientSeatIndex === 1);
                const bottomSeat = isBlack ? 1 : 0;
                const topSeat = isBlack ? 0 : 1;

                const bottomP = data.players.find(p => p.seat_index === bottomSeat);
                const topP = data.players.find(p => p.seat_index === topSeat);

                if (bottomP) {
                    const bName = document.getElementById('bottomPlayerName');
                    const bRating = document.getElementById('bottomPlayerRating');
                    if (bName) bName.innerText = bottomP.player_name || 'You';
                    if (bRating) bRating.innerText = `(${bottomP.rating || 1200})`;
                }
                if (topP) {
                    const tName = document.getElementById('topPlayerName');
                    const tRating = document.getElementById('topPlayerRating');
                    if (tName) tName.innerText = topP.player_name || 'Opponent';
                    if (tRating) tRating.innerText = `(${topP.rating || 1200})`;
                }

                renderStandardChessBoard(state, data.client_valid_moves, clientSeatIndex);

            } else if (gameType === 'CHESS_4WAY') {
                const currentP = state.players[state.current_player_index];
                turnColor = currentP ? currentP.color : 'red';
                const isMyTurn = (state.current_player_index === clientSeatIndex);
                turnStatusText.innerText = isMyTurn ? `Your Turn! (${currentP.name})` : `Turn: ${currentP.name}`;
                render4WayChessBoard(state, data.client_valid_moves, clientSeatIndex);

            } else if (gameType === 'CHESS_BUGHOUSE') {
                renderBughouseChessBoard(state, data.client_valid_moves, clientSeatIndex);
            }
        }

        currentTurnColorIndicator.style.backgroundColor = getColorHex(turnColor);
    }
}

// WebSocket Sender Helpers
function sendSelectSeat(seatIndex = null) {
    const color = document.getElementById('colorPicker').value;
    socket.send(jsonPayload('select_seat', { seat_index: seatIndex, color: color }));
}

function sendToggleReady() {
    socket.send(jsonPayload('toggle_ready'));
}

function sendStartGame() {
    socket.send(jsonPayload('start_game'));
}

function sendKickPlayer(seatIndex) {
    socket.send(jsonPayload('kick_player', { seat_index: seatIndex }));
}

function sendRollDice() {
    socket.send(jsonPayload('game_action', { type: 'roll_dice' }));
}

function sendMovePiece(actionData) {
    socket.send(jsonPayload('game_action', actionData));
}

function jsonPayload(action, payload = {}) {
    return JSON.stringify({ action: action, payload: payload });
}

function showError(msg) {
    const toast = document.getElementById('errorToast');
    const msgSpan = document.getElementById('errorMessage');
    msgSpan.innerText = msg;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 5000);
}

function getColorHex(colorName) {
    const map = {
        'red': '#ef4444',
        'blue': '#3b82f6',
        'green': '#10b981',
        'yellow': '#eab308',
        'purple': '#a855f7',
        'orange': '#f97316',
        'cyan': '#06b6d4',
        'pink': '#ec4899',
        'white': '#f8fafc',
        'black': '#334155'
    };
    return map[colorName] || '#6366f1';
}

document.addEventListener('DOMContentLoaded', initWebSocket);
