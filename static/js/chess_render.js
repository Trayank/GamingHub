// chess_render.js - SVG & Canvas Renderers with Drag-and-Drop, Move Audio Triggers, and Destination Dots

let selectedSquare = null;
let selectedReservePiece = null;

const UNICODE_PIECES = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
    'R_r': '♜', 'N_r': '♞', 'B_r': '♝', 'Q_r': '♛', 'K_r': '♚', 'P_r': '♟',
    'R_b': '♜', 'N_b': '♞', 'B_b': '♝', 'Q_b': '♛', 'K_b': '♚', 'P_b': '♟',
    'R_y': '♜', 'N_y': '♞', 'B_y': '♝', 'Q_y': '♛', 'K_y': '♚', 'P_y': '♟',
    'R_g': '♜', 'N_g': '♞', 'B_g': '♝', 'Q_g': '♛', 'K_g': '♚', 'P_g': '♟'
};

// Web Audio API Synthesizer for Chess Sound Triggers
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playSound(type) {
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    if (type === 'move') {
        osc.frequency.setValueAtTime(300, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.1);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.1);
    } else if (type === 'capture') {
        osc.frequency.setValueAtTime(600, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.15);
    } else if (type === 'check') {
        osc.frequency.setValueAtTime(800, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.25);
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

    // Render 8x8 Board
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const isLight = (r + c) % 2 === 0;
            ctx.fillStyle = isLight ? '#cbd5e1' : '#475569';
            ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);

            // Highlight selected square
            if (selectedSquare && selectedSquare[0] === r && selectedSquare[1] === c) {
                ctx.fillStyle = 'rgba(234, 179, 8, 0.5)';
                ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
            }

            // Legal Move Destination Green Dots
            if (selectedSquare) {
                const isValidDest = moves.some(m => m.from[0] === selectedSquare[0] && m.from[1] === selectedSquare[1] && m.to[0] === r && m.to[1] === c);
                if (isValidDest) {
                    ctx.beginPath();
                    ctx.arc(c * tileSize + tileSize / 2, r * tileSize + tileSize / 2, tileSize / 6, 0, Math.PI * 2);
                    ctx.fillStyle = '#10b981';
                    ctx.fill();
                }
            }

            // Draw Piece
            const piece = board[r][c];
            if (piece && piece !== '.') {
                ctx.font = `${tileSize * 0.75}px serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = (piece === piece.toUpperCase()) ? '#f8fafc' : '#0f172a';
                ctx.fillText(UNICODE_PIECES[piece] || piece, c * tileSize + tileSize / 2, r * tileSize + tileSize / 2);
            }
        }
    }

    // Interactive Click Handler
    canvas.onclick = function(e) {
        const rect = canvas.getBoundingClientRect();
        const clickX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const clickY = (e.clientY - rect.top) * (canvas.height / rect.height);
        const c = Math.floor(clickX / tileSize);
        const r = Math.floor(clickY / tileSize);

        // Handle Bughouse Drop if a reserve piece is selected
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
            ctx.fillStyle = isLight ? '#cbd5e1' : '#475569';
            ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);

            if (selectedSquare && selectedSquare[0] === r && selectedSquare[1] === c) {
                ctx.fillStyle = 'rgba(234, 179, 8, 0.5)';
                ctx.fillRect(c * tileSize, r * tileSize, tileSize, tileSize);
            }

            // Destination dots for 4-Way
            if (selectedSquare) {
                const isValidDest = moves.some(m => m.from[0] === selectedSquare[0] && m.from[1] === selectedSquare[1] && m.to[0] === r && m.to[1] === c);
                if (isValidDest) {
                    ctx.beginPath();
                    ctx.arc(c * tileSize + tileSize / 2, r * tileSize + tileSize / 2, tileSize / 6, 0, Math.PI * 2);
                    ctx.fillStyle = '#10b981';
                    ctx.fill();
                }
            }

            if (sq && sq !== '.') {
                let colorHex = '#94a3b8'; // Grey for eliminated obstacles
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
            if (board[r][c] && board[r][c] !== '.' && !board[r][c].startswith('X_')) {
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

    // Render Bughouse reserve bank palette
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
