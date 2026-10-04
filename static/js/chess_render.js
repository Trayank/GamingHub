// chess_render.js - Chess.com Style Canvas Renderer & Web Audio API Engine

let selectedSquare = null;
let selectedReservePiece = null;
let lastMoveSquares = null; // { from: [r,c], to: [r,c] }

const UNICODE_PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
    'R_r': '♜', 'N_r': '♞', 'B_r': '♝', 'Q_r': '♛', 'K_r': '♚', 'P_r': '♟',
    'R_b': '♜', 'N_b': '♞', 'B_b': '♝', 'Q_b': '♛', 'K_b': '♚', 'P_b': '♟',
    'R_y': '♜', 'N_y': '♞', 'B_y': '♝', 'Q_y': '♛', 'K_y': '♚', 'P_y': '♟',
    'R_g': '♜', 'N_g': '♞', 'B_g': '♝', 'Q_g': '♛', 'K_g': '♚', 'P_g': '♟'
};

const PIECE_VALUES = {
    'P': 1, 'p': 1,
    'N': 3, 'n': 3,
    'B': 3, 'b': 3,
    'R': 5, 'r': 5,
    'Q': 9, 'q': 9,
    'K': 0, 'k': 0
};

// Web Audio API Synthesizer for Chess Sound Effects
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playSound(type) {
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (type === 'move') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(320, now);
        osc.frequency.exponentialRampToValueAtTime(120, now + 0.08);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);
        osc.start(now);
        osc.stop(now + 0.08);
    } else if (type === 'capture') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(580, now);
        osc.frequency.exponentialRampToValueAtTime(180, now + 0.12);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.12);
        osc.start(now);
        osc.stop(now + 0.12);
    } else if (type === 'check') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, now);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
    } else if (type === 'castle') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(554, now + 0.08);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.16);
        osc.start(now);
        osc.stop(now + 0.16);
    } else if (type === 'gameover') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523, now);
        osc.frequency.setValueAtTime(659, now + 0.15);
        osc.frequency.setValueAtTime(783, now + 0.3);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
        osc.start(now);
        osc.stop(now + 0.5);
    }
}

function renderStandardChessBoard(state, validMovesInfo, clientSeatIndex) {
    const canvas = document.getElementById('gameBoardCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const tileSize = width / 8;

    ctx.clearRect(0, 0, width, height);

    const board = state.board_matrix;
    const moves = (validMovesInfo && validMovesInfo.moves) ? validMovesInfo.moves : [];

    // Track last move if present
    if (state.move_history && state.move_history.length > 0) {
        const lastMove = state.move_history[state.move_history.length - 1];
        if (lastMove.uci && lastMove.uci.length >= 4) {
            const files = 'abcdefgh';
            const f1 = files.indexOf(lastMove.uci[0]);
            const r1 = 8 - parseInt(lastMove.uci[1]);
            const f2 = files.indexOf(lastMove.uci[2]);
            const r2 = 8 - parseInt(lastMove.uci[3]);
            lastMoveSquares = { from: [r1, f1], to: [r2, f2] };
        }
    }

    const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
    const ranks = ['8', '7', '6', '5', '4', '3', '2', '1'];

    // Render 8x8 Board (Chess.com Green theme: #eeeed2 light, #769656 dark)
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const isLight = (r + c) % 2 === 0;
            ctx.fillStyle = isLight ? '#eeeed2' : '#769656';
            ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);

            // Last Move Yellow Highlight
            if (lastMoveSquares) {
                if ((lastMoveSquares.from[0] === r && lastMoveSquares.from[1] === c) ||
                    (lastMoveSquares.to[0] === r && lastMoveSquares.to[1] === c)) {
                    ctx.fillStyle = 'rgba(255, 255, 0, 0.42)';
                    ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
                }
            }

            // Selected Square Highlight
            if (selectedSquare && selectedSquare[0] === r && selectedSquare[1] === c) {
                ctx.fillStyle = 'rgba(186, 202, 68, 0.8)';
                ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
            }

            // King Check Red Radial Glow
            const piece = board[r][c];
            if (state.is_check && piece) {
                const turnColor = state.current_turn;
                if ((turnColor === 'w' && piece === 'K') || (turnColor === 'b' && piece === 'k')) {
                    const grad = ctx.createRadialGradient(
                        c * tileSize + tileSize / 2, r * tileSize + tileSize / 2, 5,
                        c * tileSize + tileSize / 2, r * tileSize + tileSize / 2, tileSize * 0.6
                    );
                    grad.addColorStop(0, 'rgba(239, 68, 68, 0.9)');
                    grad.addColorStop(1, 'rgba(239, 68, 68, 0)');
                    ctx.fillStyle = grad;
                    ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
                }
            }

            // Legal Move Destination Green Dots / Capture Rings
            if (selectedSquare) {
                const matchedMove = moves.find(m => m.from[0] === selectedSquare[0] && m.from[1] === selectedSquare[1] && m.to[0] === r && m.to[1] === c);
                if (matchedMove) {
                    if (piece !== '.') {
                        // Capture Ring
                        ctx.beginPath();
                        ctx.arc(c * tileSize + tileSize / 2, r * tileSize + tileSize / 2, tileSize * 0.42, 0, Math.PI * 2);
                        ctx.strokeStyle = 'rgba(239, 68, 68, 0.7)';
                        ctx.lineWidth = 4;
                        ctx.stroke();
                    } else {
                        // Solid destination dot
                        ctx.beginPath();
                        ctx.arc(c * tileSize + tileSize / 2, r * tileSize + tileSize / 2, tileSize / 6, 0, Math.PI * 2);
                        ctx.fillStyle = 'rgba(16, 185, 129, 0.7)';
                        ctx.fill();
                    }
                }
            }

            // Draw Board Coordinates inside rank 1 and file A
            ctx.font = 'bold 10px Outfit, sans-serif';
            if (c === 0) {
                ctx.fillStyle = isLight ? '#769656' : '#eeeed2';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                ctx.fillText(ranks[r], 3, r * tileSize + 3);
            }
            if (r === 7) {
                ctx.fillStyle = isLight ? '#769656' : '#eeeed2';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'bottom';
                ctx.fillText(files[c], (c + 1) * tileSize - 3, 8 * tileSize - 3);
            }

            // Draw Piece
            if (piece && piece !== '.') {
                ctx.font = `${tileSize * 0.75}px serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = (piece === piece.toUpperCase()) ? '#ffffff' : '#1e293b';
                
                // Add drop shadow for depth
                ctx.shadowColor = 'rgba(0, 0, 0, 0.35)';
                ctx.shadowBlur = 4;
                ctx.fillText(UNICODE_PIECES[piece] || piece, c * tileSize + tileSize / 2, r * tileSize + tileSize / 2);
                ctx.shadowBlur = 0;
            }
        }
    }

    // Update Player Cards HUD & PGN Move List
    updateChessHUD(state, clientSeatIndex);

    // Interactive Click Handler
    canvas.onclick = function(e) {
        const rect = canvas.getBoundingClientRect();
        const clickX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const clickY = (e.clientY - rect.top) * (canvas.height / rect.height);
        const c = Math.floor(clickX / tileSize);
        const r = Math.floor(clickY / tileSize);

        if (selectedReservePiece) {
            sendMovePiece({
                type: 'drop_piece',
                piece: selectedReservePiece,
                to: [r, c]
            });
            playSound('move');
            selectedReservePiece = null;
            return;
        }

        if (!selectedSquare) {
            if (board[r][c] !== '.') {
                selectedSquare = [r, c];
                renderStandardChessBoard(state, validMovesInfo, clientSeatIndex);
            }
        } else {
            const fromSq = selectedSquare;
            const toSq = [r, c];

            if (fromSq[0] === toSq[0] && fromSq[1] === toSq[1]) {
                selectedSquare = null;
            } else {
                const isCapture = (board[r][c] !== '.');
                sendMovePiece({
                    type: 'move_piece',
                    from: fromSq,
                    to: toSq,
                    promotion: 'Q'
                });
                playSound(isCapture ? 'capture' : 'move');
                selectedSquare = null;
            }
            renderStandardChessBoard(state, validMovesInfo, clientSeatIndex);
        }
    };
}

function updateChessHUD(state, clientSeatIndex) {
    const moveHistoryContainer = document.getElementById('matchLogContainer');
    if (moveHistoryContainer && state.move_history) {
        let pgnHtml = '<div class="grid grid-cols-2 gap-x-2 gap-y-1 text-xs font-mono">';
        for (let i = 0; i < state.move_history.length; i += 2) {
            const moveNum = Math.floor(i / 2) + 1;
            const whiteMove = state.move_history[i] ? (state.move_history[i].san || state.move_history[i].uci) : '';
            const blackMove = state.move_history[i + 1] ? (state.move_history[i + 1].san || state.move_history[i + 1].uci) : '';

            pgnHtml += `<div class="text-slate-400 font-semibold">${moveNum}. ${whiteMove}</div>`;
            pgnHtml += `<div class="text-slate-200">${blackMove}</div>`;
        }
        pgnHtml += '</div>';
        moveHistoryContainer.innerHTML = pgnHtml;
    }

    // Material Advantage Score & Graveyards
    const whiteCaps = state.captured_pieces ? state.captured_pieces.w : [];
    const blackCaps = state.captured_pieces ? state.captured_pieces.b : [];

    const whiteVal = whiteCaps.reduce((acc, p) => acc + (PIECE_VALUES[p] || 0), 0);
    const blackVal = blackCaps.reduce((acc, p) => acc + (PIECE_VALUES[p] || 0), 0);

    const diff = whiteVal - blackVal;

    const isBlack = (clientSeatIndex === 1);
    const bottomCaps = isBlack ? blackCaps : whiteCaps;
    const topCaps = isBlack ? whiteCaps : blackCaps;

    const topAdv = document.getElementById('topPlayerAdvantage');
    const bottomAdv = document.getElementById('bottomPlayerAdvantage');

    if (topAdv && bottomAdv) {
        topAdv.innerText = (isBlack ? diff > 0 : diff < 0) ? `+${Math.abs(diff)}` : '';
        bottomAdv.innerText = (isBlack ? diff < 0 : diff > 0) ? `+${Math.abs(diff)}` : '';
    }

    const topGrave = document.getElementById('topPlayerGraveyard');
    const bottomGrave = document.getElementById('bottomPlayerGraveyard');

    if (topGrave) {
        topGrave.innerHTML = topCaps.map(p => `<span class="text-sm font-semibold">${UNICODE_PIECES[p] || p}</span>`).join(' ');
    }
    if (bottomGrave) {
        bottomGrave.innerHTML = bottomCaps.map(p => `<span class="text-sm font-semibold">${UNICODE_PIECES[p] || p}</span>`).join(' ');
    }

    // Active Turn Player Card Border Highlights
    const isTopTurn = (isBlack ? state.current_turn === 'w' : state.current_turn === 'b');
    const isBottomTurn = (isBlack ? state.current_turn === 'b' : state.current_turn === 'w');

    const topCard = document.getElementById('topPlayerCard');
    const bottomCard = document.getElementById('bottomPlayerCard');

    if (topCard) {
        if (isTopTurn) {
            topCard.classList.add('border-emerald-500/80', 'bg-emerald-500/10');
            topCard.classList.remove('border-slate-800');
        } else {
            topCard.classList.remove('border-emerald-500/80', 'bg-emerald-500/10');
            topCard.classList.add('border-slate-800');
        }
    }
    if (bottomCard) {
        if (isBottomTurn) {
            bottomCard.classList.add('border-emerald-500/80', 'bg-emerald-500/10');
            bottomCard.classList.remove('border-slate-800');
        } else {
            bottomCard.classList.remove('border-emerald-500/80', 'bg-emerald-500/10');
            bottomCard.classList.add('border-slate-800');
        }
    }
}

// Modal & Action Controls Handlers
function openResignModal() {
    const modal = document.getElementById('resignModal');
    if (modal) modal.classList.remove('hidden');
}

function closeResignModal() {
    const modal = document.getElementById('resignModal');
    if (modal) modal.classList.add('hidden');
}

function confirmResign() {
    closeResignModal();
    if (typeof socket !== 'undefined' && socket) {
        socket.send(jsonPayload('game_action', { type: 'resign' }));
    }
    playSound('gameover');
}

function sendOfferDraw() {
    if (typeof socket !== 'undefined' && socket) {
        socket.send(jsonPayload('game_action', { type: 'offer_draw' }));
    }
}

function sendRematch() {
    if (typeof socket !== 'undefined' && socket) {
        socket.send(jsonPayload('game_action', { type: 'rematch' }));
    }
}

function sendReaction(emoji) {
    showReactionAnimation(emoji);
    if (typeof socket !== 'undefined' && socket) {
        socket.send(jsonPayload('game_action', { type: 'reaction', emoji: emoji }));
    }
}

function showReactionAnimation(emoji) {
    const overlay = document.getElementById('reactionOverlay');
    if (!overlay) return;
    const bubble = document.createElement('div');
    bubble.className = 'absolute text-5xl animate-bounce transition-all duration-1000 opacity-100';
    bubble.innerText = emoji;
    overlay.appendChild(bubble);
    setTimeout(() => {
        bubble.classList.add('opacity-0', 'scale-150', '-translate-y-12');
        setTimeout(() => bubble.remove(), 1000);
    }, 800);
}

function render4WayChessBoard(state, validMovesInfo, clientSeatIndex) {
    const canvas = document.getElementById('gameBoardCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const tileSize = width / 14;

    ctx.clearRect(0, 0, width, height);
    const board = state.board;
    const moves = (validMovesInfo && validMovesInfo.moves) ? validMovesInfo.moves : [];

    for (let r = 0; r < 14; r++) {
        for (let c = 0; c < 14; c++) {
            const sq = board[r][c];
            if (sq === null) {
                ctx.fillStyle = '#090d16';
                ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
                continue;
            }

            const isLight = (r + c) % 2 === 0;
            ctx.fillStyle = isLight ? '#eeeed2' : '#769656';
            ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);

            if (selectedSquare && selectedSquare[0] === r && selectedSquare[1] === c) {
                ctx.fillStyle = 'rgba(186, 202, 68, 0.8)';
                ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
            }

            if (selectedSquare) {
                const isValidDest = moves.some(m => m.from[0] === selectedSquare[0] && m.from[1] === selectedSquare[1] && m.to[0] === r && m.to[1] === c);
                if (isValidDest) {
                    ctx.beginPath();
                    ctx.arc(c * tileSize + tileSize / 2, r * tileSize + tileSize / 2, tileSize / 6, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(16, 185, 129, 0.7)';
                    ctx.fill();
                }
            }

            if (sq && sq !== '.') {
                let colorHex = '#94a3b8';
                if (!sq.startsWith('X_')) {
                    const ownerCode = sq.split('_')[1];
                    colorHex = ownerCode === 'r' ? '#ef4444' : ownerCode === 'b' ? '#3b82f6' : ownerCode === 'y' ? '#eab308' : '#10b981';
                }

                ctx.font = `${tileSize * 0.75}px serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = colorHex;
                ctx.fillText(UNICODE_PIECES[sq] || sq[0], c * tileSize + tileSize / 2, r * tileSize + tileSize / 2);
            }
        }
    }

    canvas.onclick = function(e) {
        const rect = canvas.getBoundingClientRect();
        const clickX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const clickY = (e.clientY - rect.top) * (canvas.height / rect.height);
        const c = Math.floor(clickX / tileSize);
        const r = Math.floor(clickY / tileSize);

        if (!selectedSquare) {
            if (board[r][c] && board[r][c] !== '.' && !board[r][c].startsWith('X_')) {
                selectedSquare = [r, c];
                render4WayChessBoard(state, validMovesInfo, clientSeatIndex);
            }
        } else {
            const fromSq = selectedSquare;
            const toSq = [r, c];
            const isCapture = (board[r][c] !== '.');
            sendMovePiece({
                type: 'move_piece',
                from: fromSq,
                to: toSq
            });
            playSound(isCapture ? 'capture' : 'move');
            selectedSquare = null;
            render4WayChessBoard(state, validMovesInfo, clientSeatIndex);
        }
    };
}

function renderBughouseChessBoard(state, validMovesInfo, clientSeatIndex) {
    const isBoardA = (clientSeatIndex === 0 || clientSeatIndex === 1);
    const subState = isBoardA ? state.board_a : state.board_b;
    renderStandardChessBoard(subState, validMovesInfo, clientSeatIndex);

    const reservePanel = document.getElementById('bughouseReservePanel');
    const reserveList = document.getElementById('reservePiecesList');
    if (reservePanel && reserveList) {
        reservePanel.classList.remove('hidden');
        reserveList.innerHTML = '';
        const myReserve = state.reserves[clientSeatIndex] || [];
        myReserve.forEach(piece => {
            const btn = document.createElement('button');
            const isSelected = (selectedReservePiece === piece);
            btn.className = isSelected 
                ? 'px-3 py-1 bg-amber-500 text-slate-900 font-bold border-2 border-amber-300 rounded text-xl shadow-lg'
                : 'px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded text-xl text-white';
            btn.innerText = UNICODE_PIECES[piece] || piece;
            btn.onclick = function() {
                selectedReservePiece = isSelected ? null : piece;
                renderBughouseChessBoard(state, validMovesInfo, clientSeatIndex);
            };
            reserveList.appendChild(btn);
        });
    }
}
