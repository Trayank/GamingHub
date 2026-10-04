// room_ws.js - WebSocket client manager for GamingHub
let socket = null;
let currentRoomData = null;
let clientSeatIndex = -1;

function initWebSocket() {
    startLobbyPolling();

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
    } else if (message.type === 'quick_phrase' && message.phrase) {
        if (typeof showQuickPhraseBubble === 'function') {
            showQuickPhraseBubble(message.phrase, message.sender_name || 'Player');
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
            turnStatusText.innerText = isMyTurn ? `Your Turn! (${currentP ? currentP.name : 'Player'})` : `Turn: ${currentP ? currentP.name : 'Player'}`;
            
            // Start/Reset 15-second Turn Timer
            startTurnTimer(isMyTurn, state.phase);

            // Show Ludo controls
            const ludoCtrl = document.getElementById('ludoControls');
            if (ludoCtrl) ludoCtrl.classList.remove('hidden');
            const bugCtrl = document.getElementById('bughouseReservePanel');
            if (bugCtrl) bugCtrl.classList.add('hidden');

            const rollBtn = document.getElementById('rollDiceBtn');
            const canRoll = data.client_valid_moves && data.client_valid_moves.can_roll;
            if (rollBtn) {
                rollBtn.disabled = !canRoll;
                rollBtn.className = canRoll 
                    ? "w-full py-3 bg-gradient-to-r from-amber-500 to-red-600 hover:from-amber-400 hover:to-red-500 text-white font-extrabold text-xs rounded-xl shadow-lg transition tracking-wider uppercase cursor-pointer"
                    : "w-full py-3 bg-slate-800 text-slate-500 font-bold text-xs rounded-xl cursor-not-allowed opacity-60";
            }

            if (state.dice_value !== null && state.dice_value !== undefined) {
                const cube = document.getElementById('diceCube');
                if (cube) {
                    cube.className = `dice-cube show-${state.dice_value}`;
                }
            }

            // Auto-Move Automation: If exactly 1 token has a legal move on client's turn, hop it forward automatically
            if (isMyTurn && state.phase === 'WAITING_FOR_MOVE' && data.client_valid_moves) {
                const validIds = data.client_valid_moves.valid_token_ids || [];
                if (validIds.length === 1) {
                    if (!window._autoMoveTimeout) {
                        window._autoMoveTimeout = setTimeout(() => {
                            window._autoMoveTimeout = null;
                            sendMovePiece({ type: 'move_piece', token_id: validIds[0] });
                        }, 400);
                    }
                }
            }

            if (state.phase === 'GAME_OVER') {
                showVictoryPodiumModal(state);
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

// WebSocket Sender Helpers & HTTP Polling Fallback
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue || '';
}

let statusPollingInterval = null;

function startLobbyPolling() {
    if (statusPollingInterval) clearInterval(statusPollingInterval);
    fetchStatusAndUpdateLobby();
    statusPollingInterval = setInterval(fetchStatusAndUpdateLobby, 2000);
}

function fetchStatusAndUpdateLobby() {
    if (typeof ROOM_CODE === 'undefined' || !ROOM_CODE) return;
    fetch(`/room/${ROOM_CODE}/status/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(res => {
        if (res.status === 404) {
            window.location.href = '/?error=Room+session+expired+or+server+restarted.';
            return;
        }
        return res.json();
    })
    .then(data => {
        if (!data) return;
        if (data.status === 'in_progress' || data.status === 'PLAYING') {
            const lobbyView = document.getElementById('lobbyView');
            const gameView = document.getElementById('gameView');
            if (lobbyView && gameView && !lobbyView.classList.contains('hidden')) {
                lobbyView.classList.add('hidden');
                gameView.classList.remove('hidden');
            }
        }
        updateLobbyUIFromPolling(data);
    })
    .catch(err => console.error('Status polling error:', err));
}

function updateLobbyUIFromPolling(data) {
    if (!data || !data.players) return;
    const grid = document.getElementById('playerSeatsGrid');
    if (!grid) return;

    // Update Connected Players Badge
    const countBadge = document.getElementById('playerCountBadge');
    if (countBadge) {
        countBadge.innerText = `Connected Players (${data.player_count}/${data.max_players})`;
    }

    // Host Badge & Controls
    const hostBadge = document.getElementById('hostBadge');
    const hostControls = document.getElementById('hostControls');
    const startBtn = document.getElementById('startGameBtn');
    const toggleReadyBtn = document.getElementById('toggleReadyBtn');

    if (data.is_current_user_host) {
        if (hostBadge) hostBadge.classList.remove('hidden');
        if (hostControls) hostControls.classList.remove('hidden');
        if (startBtn) {
            startBtn.disabled = !data.can_start;
            startBtn.className = data.can_start
                ? "bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold py-2.5 px-8 rounded-xl shadow-lg shadow-indigo-600/30 transition cursor-pointer"
                : "bg-slate-800 text-slate-500 border border-slate-700 font-bold py-2.5 px-8 rounded-xl cursor-not-allowed opacity-60";
            startBtn.innerText = data.can_start ? "🚀 Start Game" : `Waiting for Ready (${data.player_count}/${data.max_players})`;
        }
    } else {
        if (hostBadge) hostBadge.classList.add('hidden');
        if (hostControls) hostControls.classList.remove('hidden');
        if (startBtn) {
            startBtn.disabled = true;
            startBtn.className = "bg-slate-800 text-slate-400 border border-slate-700 font-semibold py-2.5 px-6 rounded-xl cursor-not-allowed opacity-80";
            startBtn.innerText = "⏳ Waiting for host to start game...";
        }
    }

    // Render Player Cards Grid
    grid.innerHTML = '';
    data.players.forEach((player, idx) => {
        const card = document.createElement('div');
        card.className = 'glass-panel p-4 rounded-xl border border-slate-700 flex flex-col justify-between space-y-3';
        const isMe = (player.session_key === RECONNECT_TOKEN || player.session_key === SESSION_KEY);

        if (isMe && toggleReadyBtn) {
            toggleReadyBtn.innerText = player.is_ready ? '✓ Ready (Click to Unready)' : '⏳ Set Ready';
            toggleReadyBtn.className = player.is_ready 
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 px-6 rounded-xl shadow-lg transition'
                : 'bg-amber-600 hover:bg-amber-500 text-white font-semibold py-2.5 px-6 rounded-xl shadow-lg transition';
        }

        card.innerHTML = `
            <div class="flex justify-between items-start">
                <span class="text-xs font-bold text-slate-400">Seat #${idx + 1}</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${player.is_ready ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'}">
                    ${player.is_ready ? '✓ Ready' : '⏳ Waiting'}
                </span>
            </div>
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xl">
                    ${player.avatar || '🧙'}
                </div>
                <div>
                    <div class="font-bold text-white flex items-center space-x-1">
                        <span>${player.name}</span>
                        ${isMe ? '<span class="text-xs text-indigo-400 font-normal">(You)</span>' : ''}
                        ${player.is_host ? '<span class="text-amber-400 text-xs font-bold">👑 Host</span>' : ''}
                    </div>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function sendSelectSeat(seatIndex = null) {
    const color = document.getElementById('colorPicker').value;
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(jsonPayload('select_seat', { seat_index: seatIndex, color: color }));
    }
}

function sendToggleReady() {
    fetch(`/room/${ROOM_CODE}/toggle-ready/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => res.json())
    .then(() => fetchStatusAndUpdateLobby())
    .catch(err => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(jsonPayload('toggle_ready'));
        }
    });
}

function sendStartGame() {
    fetch(`/room/${ROOM_CODE}/start/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            if (data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                fetchStatusAndUpdateLobby();
            }
        } else {
            showError(data.error || 'Failed to start game');
        }
    })
    .catch(err => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(jsonPayload('start_game'));
        }
    });
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

let turnTimerInterval = null;
let turnTimeRemaining = 15;

function startTurnTimer(isMyTurn, phase) {
    if (turnTimerInterval) clearInterval(turnTimerInterval);
    turnTimeRemaining = 15;
    updateTurnTimerDisplay();

    turnTimerInterval = setInterval(() => {
        turnTimeRemaining--;
        updateTurnTimerDisplay();

        if (turnTimeRemaining <= 0) {
            clearInterval(turnTimerInterval);
            if (isMyTurn) {
                if (phase === 'WAITING_FOR_ROLL') {
                    triggerDiceRollAnimation();
                }
            }
        }
    }, 1000);
}

function updateTurnTimerDisplay() {
    const banner = document.getElementById('turnStatusText');
    if (!banner) return;
    const colorClass = turnTimeRemaining > 10 ? 'text-emerald-400' : (turnTimeRemaining > 5 ? 'text-amber-400' : 'text-red-400');
    let timerBadge = document.getElementById('turnTimerBadge');
    if (!timerBadge) {
        timerBadge = document.createElement('span');
        timerBadge.id = 'turnTimerBadge';
        timerBadge.className = `ml-2 font-mono text-xs font-bold ${colorClass} px-2 py-0.5 rounded bg-slate-800 border border-slate-700`;
        banner.appendChild(timerBadge);
    }
    timerBadge.className = `ml-2 font-mono text-xs font-bold ${colorClass} px-2 py-0.5 rounded bg-slate-800 border border-slate-700`;
    timerBadge.innerText = `⏱ ${turnTimeRemaining}s`;
}

function triggerDiceRollAnimation() {
    if (typeof playLudoSound === 'function') {
        playLudoSound('dice');
    }
    const cube = document.getElementById('diceCube');
    if (cube) {
        cube.classList.add('rolling');
        setTimeout(() => cube.classList.remove('rolling'), 600);
    }
    sendRollDice();
}

function showVictoryPodiumModal(state) {
    const modal = document.getElementById('podiumModal');
    const podiumList = document.getElementById('podiumList');
    if (!modal || !podiumList) return;

    modal.classList.remove('hidden');
    podiumList.innerHTML = '';

    const rankings = state.rankings || [];
    const positions = [
        { rank: 2, height: 'h-24', bg: 'bg-slate-700', label: '🥈 2nd', color: 'text-slate-300' },
        { rank: 1, height: 'h-32', bg: 'bg-amber-500', label: '🥇 1st', color: 'text-amber-300' },
        { rank: 3, height: 'h-20', bg: 'bg-amber-800', label: '🥉 3rd', color: 'text-amber-600' }
    ];

    positions.forEach(pos => {
        const entry = rankings.find(r => r.rank === pos.rank) || (pos.rank === 1 && state.winner !== null ? { name: state.players[state.winner].name } : null);
        const col = document.createElement('div');
        col.className = 'flex flex-col items-center justify-end';
        col.innerHTML = `
            <div class="font-bold text-xs text-white mb-1">${entry ? entry.name : '-'}</div>
            <div class="${pos.height} w-20 ${pos.bg} rounded-t-2xl flex items-center justify-center border-t-2 border-amber-300/40 shadow-lg">
                <span class="font-black text-xs text-white">${pos.label}</span>
            </div>
        `;
        podiumList.appendChild(col);
    });

    triggerConfettiAnimation();
    if (typeof playLudoSound === 'function') {
        playLudoSound('win');
    }
}

function triggerConfettiAnimation() {
    const canvas = document.getElementById('confettiCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;

    const particles = [];
    const colors = ['#ef4444', '#3b82f6', '#eab308', '#10b981', '#a855f7', '#ec4899'];

    for (let i = 0; i < 80; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height - canvas.height,
            r: Math.random() * 6 + 4,
            color: colors[Math.floor(Math.random() * colors.length)],
            vx: (Math.random() - 0.5) * 2,
            vy: Math.random() * 3 + 2,
            rot: Math.random() * 360,
            vRot: (Math.random() - 0.5) * 10
        });
    }

    function renderConfetti() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.rot += p.vRot;
            if (p.y > canvas.height) p.y = -10;

            ctx.save();
            ctx.translate(p.x, p.y);
            ctx.rotate((p.rot * Math.PI) / 180);
            ctx.fillStyle = p.color;
            ctx.fillRect(-p.r, -p.r, p.r * 2, p.r * 2);
            ctx.restore();
        });
        requestAnimationFrame(renderConfetti);
    }
    renderConfetti();
}

document.addEventListener('DOMContentLoaded', initWebSocket);
