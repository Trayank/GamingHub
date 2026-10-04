// ludo_render.js - Authentic Ludo King Style Render Engine & Web Audio Synthesizer

let previousTokenStates = {}; // Key: "pIndex_tId" -> { state, pos }
let animatedTokens = {};       // Key: "pIndex_tId" -> { currentR, currentC, isHopping, arcOffset }

// Web Audio API Synthesizer for Ludo Sound Effects
const ludoAudioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playLudoSound(type) {
    if (ludoAudioCtx.state === 'suspended') {
        ludoAudioCtx.resume();
    }
    const now = ludoAudioCtx.currentTime;
    const osc = ludoAudioCtx.createOscillator();
    const gain = ludoAudioCtx.createGain();
    osc.connect(gain);
    gain.connect(ludoAudioCtx.destination);

    if (type === 'dice') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(450, now);
        osc.frequency.exponentialRampToValueAtTime(150, now + 0.15);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
        osc.start(now);
        osc.stop(now + 0.15);
    } else if (type === 'step') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(600, now);
        osc.frequency.exponentialRampToValueAtTime(300, now + 0.08);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);
        osc.start(now);
        osc.stop(now + 0.08);
    } else if (type === 'capture') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(120, now + 0.25);
        gain.gain.setValueAtTime(0.4, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
    } else if (type === 'home') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.setValueAtTime(659.25, now + 0.1); // E5
        osc.frequency.setValueAtTime(783.99, now + 0.2); // G5
        gain.gain.setValueAtTime(0.35, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
        osc.start(now);
        osc.stop(now + 0.4);
    } else if (type === 'win') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523, now);
        osc.frequency.setValueAtTime(659, now + 0.15);
        osc.frequency.setValueAtTime(783, now + 0.3);
        osc.frequency.setValueAtTime(1046, now + 0.45);
        gain.gain.setValueAtTime(0.4, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.8);
        osc.start(now);
        osc.stop(now + 0.8);
    } else if (type === 'phrase') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.setValueAtTime(1174, now + 0.08);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
        osc.start(now);
        osc.stop(now + 0.2);
    }
}

// 52 Main Circuit Track Coordinates on 15x15 Ludo Grid (Clockwise starting from Red entry square r=8, c=1)
const TRACK_COORDS_52 = [
    // Red Arm to Blue Arm (0..12)
    {r:8, c:1},  // 0: Red Start (Tile 1 / offset 0)
    {r:8, c:2},  // 1
    {r:8, c:3},  // 2
    {r:8, c:4},  // 3
    {r:8, c:5},  // 4
    {r:9, c:6},  // 5
    {r:10, c:6}, // 6
    {r:11, c:6}, // 7
    {r:12, c:6}, // 8: Red Star (Tile 8 / index 7)
    {r:13, c:6}, // 9
    {r:14, c:6}, // 10
    {r:14, c:7}, // 11
    {r:14, c:8}, // 12

    // Blue Arm to Yellow Arm (13..25)
    {r:13, c:8}, // 13: Blue Start (Tile 14 / offset 13)
    {r:12, c:8}, // 14
    {r:11, c:8}, // 15
    {r:10, c:8}, // 16
    {r:9, c:8},  // 17
    {r:8, c:9},  // 18
    {r:8, c:10}, // 19
    {r:8, c:11}, // 20
    {r:8, c:12}, // 21: Blue Star (Tile 21 / index 20)
    {r:8, c:13}, // 22
    {r:8, c:14}, // 23
    {r:7, c:14}, // 24
    {r:6, c:14}, // 25

    // Yellow Arm to Green Arm (26..38)
    {r:6, c:13}, // 26: Yellow Start (Tile 27 / offset 26)
    {r:6, c:12}, // 27
    {r:6, c:11}, // 28
    {r:6, c:10}, // 29
    {r:6, c:9},  // 30
    {r:5, c:8},  // 31
    {r:4, c:8},  // 32
    {r:3, c:8},  // 33
    {r:2, c:8},  // 34: Yellow Star (Tile 34 / index 33)
    {r:1, c:8},  // 35
    {r:0, c:8},  // 36
    {r:0, c:7},  // 37
    {r:0, c:6},  // 38

    // Green Arm to Red Arm (39..51)
    {r:1, c:6},  // 39: Green Start (Tile 40 / offset 39)
    {r:2, c:6},  // 40
    {r:3, c:6},  // 41
    {r:4, c:6},  // 42
    {r:5, c:6},  // 43
    {r:6, c:5},  // 44
    {r:6, c:4},  // 45
    {r:6, c:3},  // 46
    {r:6, c:2},  // 47: Green Star (Tile 47 / index 46)
    {r:6, c:1},  // 48
    {r:6, c:0},  // 49
    {r:7, c:0},  // 50
    {r:8, c:0}   // 51
];

function getStandardGridCoords(seatIdx, state, pos) {
    if (state === 'TRACK') {
        const startOffsets = [0, 13, 26, 39];
        const startOffset = startOffsets[seatIdx % 4];
        const absIdx = (startOffset + pos) % 52;
        return TRACK_COORDS_52[absIdx];
    } else if (state === 'STRETCH') {
        const stretchPaths = [
            [{r:7, c:1}, {r:7, c:2}, {r:7, c:3}, {r:7, c:4}, {r:7, c:5}],  // Red (Bottom-Left)
            [{r:13, c:7}, {r:12, c:7}, {r:11, c:7}, {r:10, c:7}, {r:9, c:7}], // Blue (Bottom-Right)
            [{r:7, c:13}, {r:7, c:12}, {r:7, c:11}, {r:7, c:10}, {r:7, c:9}], // Yellow (Top-Right)
            [{r:1, c:7}, {r:2, c:7}, {r:3, c:7}, {r:4, c:7}, {r:5, c:7}]   // Green (Top-Left)
        ];
        const path = stretchPaths[seatIdx % 4];
        return path[Math.min(pos, path.length - 1)];
    }
    return { r: 7, c: 7 };
}

function renderLudoBoard(state, validMovesInfo) {
    const canvas = document.getElementById('gameBoardCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const width = canvas.width;
    const height = canvas.height;
    const cx = width / 2;
    const cy = height / 2;

    ctx.clearRect(0, 0, width, height);

    // Deep slate background
    ctx.fillStyle = '#090d16';
    ctx.fillRect(0, 0, width, height);

    const playerCount = state.player_count || 4;
    const totalArms = state.total_arms || 4;
    const tokenClickTargets = [];

    detectTokenMovement(state);

    // Render full 15x15 board for 2 or 4 players
    if (totalArms === 4 || playerCount <= 4) {
        renderStandard4QuadrantLudo(ctx, width, height, state, validMovesInfo, tokenClickTargets);
    } else {
        renderPolygonalLudo(ctx, cx, cy, width, height, totalArms, state, validMovesInfo, tokenClickTargets);
    }

    // Canvas Click Event Handler
    canvas.onclick = function(e) {
        const rect = canvas.getBoundingClientRect();
        const clickX = (e.clientX - rect.left) * (canvas.width / rect.width);
        const clickY = (e.clientY - rect.top) * (canvas.height / rect.height);

        tokenClickTargets.forEach(target => {
            if (target.isSelectable) {
                const dist = Math.hypot(clickX - target.x, clickY - target.y);
                if (dist <= target.radius) {
                    sendMovePiece({ type: 'move_piece', token_id: target.tokenId });
                }
            }
        });
    };
}

function detectTokenMovement(state) {
    if (!state || !state.players) return;

    state.players.forEach(p => {
        p.tokens.forEach(token => {
            const key = `${p.id}_${token.id}`;
            const prev = previousTokenStates[key];

            if (prev) {
                if (prev.state === 'TRACK' && token.state === 'YARD') {
                    playLudoSound('capture');
                } else if (token.state === 'HOME' && prev.state !== 'HOME') {
                    playLudoSound('home');
                } else if (token.pos > prev.pos && token.state === prev.state) {
                    playLudoSound('step');
                }
            }
            previousTokenStates[key] = { state: token.state, pos: token.pos };
        });
    });
}

function renderStandard4QuadrantLudo(ctx, width, height, state, validMovesInfo, tokenClickTargets) {
    const size = Math.min(width, height);
    const grid = 15;
    const cell = size / grid;

    const LUDO_COLORS = {
        red: '#ed1c24',
        blue: '#0072bc',
        yellow: '#ffcc00',
        green: '#00a651'
    };

    // Draw Outer Board Frame
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, size, size);

    // 4 Corner Base Yards (6x6 cells each)
    const yards = [
        { r: 9, c: 0, seat: 0, color: LUDO_COLORS.red, name: 'Red' },       // Red (Bottom-Left)
        { r: 9, c: 9, seat: 1, color: LUDO_COLORS.blue, name: 'Blue' },     // Blue (Bottom-Right)
        { r: 0, c: 9, seat: 2, color: LUDO_COLORS.yellow, name: 'Yellow' }, // Yellow (Top-Right)
        { r: 0, c: 0, seat: 3, color: LUDO_COLORS.green, name: 'Green' }    // Green (Top-Left)
    ];

    yards.forEach(y => {
        ctx.fillStyle = y.color;
        ctx.fillRect(y.c * cell, y.r * cell, 6 * cell, 6 * cell);

        // White Inner Box
        ctx.fillStyle = '#ffffff';
        ctx.fillRect((y.c + 1) * cell, (y.r + 1) * cell, 4 * cell, 4 * cell);

        // 4 Yard Circle Token Holders
        const circles = [
            { r: y.r + 1.8, c: y.c + 1.8 },
            { r: y.r + 1.8, c: y.c + 4.2 },
            { r: y.r + 4.2, c: y.c + 1.8 },
            { r: y.r + 4.2, c: y.c + 4.2 }
        ];

        circles.forEach(circ => {
            ctx.beginPath();
            ctx.arc(circ.c * cell, circ.r * cell, cell * 0.55, 0, Math.PI * 2);
            ctx.fillStyle = y.color;
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2.5;
            ctx.stroke();
        });
    });

    // Center Home Triangles (3x3 grid cells: 6..8, 6..8)
    const cx = 7.5 * cell;
    const cy = 7.5 * cell;

    ctx.fillStyle = '#0f172a';
    ctx.fillRect(6 * cell, 6 * cell, 3 * cell, 3 * cell);

    drawTriangle(ctx, 6 * cell, 9 * cell, 9 * cell, 9 * cell, cx, cy, LUDO_COLORS.red);    // Bottom (Red)
    drawTriangle(ctx, 9 * cell, 6 * cell, 9 * cell, 9 * cell, cx, cy, LUDO_COLORS.blue);   // Right (Blue)
    drawTriangle(ctx, 6 * cell, 6 * cell, 9 * cell, 6 * cell, cx, cy, LUDO_COLORS.yellow); // Top (Yellow)
    drawTriangle(ctx, 6 * cell, 6 * cell, 6 * cell, 9 * cell, cx, cy, LUDO_COLORS.green);  // Left (Green)

    ctx.font = 'bold 20px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.5)';
    ctx.shadowBlur = 4;
    ctx.fillText('🏆', cx, cy);
    ctx.shadowBlur = 0;

    // Draw Grid Track Cells & Home Stretches
    for (let r = 0; r < 15; r++) {
        for (let c = 0; c < 15; c++) {
            const isYard = (r < 6 && c < 6) || (r < 6 && c > 8) || (r > 8 && c < 6) || (r > 8 && c > 8);
            const isCenter = (r >= 6 && r <= 8 && c >= 6 && c <= 8);

            if (!isYard && !isCenter) {
                ctx.strokeStyle = '#cbd5e1';
                ctx.lineWidth = 1;
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(c * cell, r * cell, cell, cell);
                ctx.strokeRect(c * cell, r * cell, cell, cell);

                // Home Stretch Colors
                if (c === 7 && r >= 9 && r <= 13) { ctx.fillStyle = LUDO_COLORS.red; ctx.fillRect(c * cell, r * cell, cell, cell); ctx.strokeRect(c * cell, r * cell, cell, cell); }
                if (r === 7 && c >= 9 && c <= 13) { ctx.fillStyle = LUDO_COLORS.blue; ctx.fillRect(c * cell, r * cell, cell, cell); ctx.strokeRect(c * cell, r * cell, cell, cell); }
                if (c === 7 && r >= 1 && r <= 5) { ctx.fillStyle = LUDO_COLORS.yellow; ctx.fillRect(c * cell, r * cell, cell, cell); ctx.strokeRect(c * cell, r * cell, cell, cell); }
                if (r === 7 && c >= 1 && c <= 5) { ctx.fillStyle = LUDO_COLORS.green; ctx.fillRect(c * cell, r * cell, cell, cell); ctx.strokeRect(c * cell, r * cell, cell, cell); }

                // Safe Start Spots (Colored with Shield/Star)
                if (r === 8 && c === 1) drawSafeSquare(ctx, c, r, cell, LUDO_COLORS.red);
                if (r === 13 && c === 8) drawSafeSquare(ctx, c, r, cell, LUDO_COLORS.blue);
                if (r === 6 && c === 13) drawSafeSquare(ctx, c, r, cell, LUDO_COLORS.yellow);
                if (r === 1 && c === 6) drawSafeSquare(ctx, c, r, cell, LUDO_COLORS.green);

                // Safe Star Spots
                if (r === 12 && c === 6) drawShieldStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.38, '#f59e0b');
                if (r === 8 && c === 12) drawShieldStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.38, '#f59e0b');
                if (r === 2 && c === 8) drawShieldStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.38, '#f59e0b');
                if (r === 6 && c === 2) drawShieldStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.38, '#f59e0b');
            }
        }
    }

    // Directional Arrows Entering Home Straight Columns
    drawArrow(ctx, (7.5) * cell, (14.5) * cell, 'UP', LUDO_COLORS.red, cell);
    drawArrow(ctx, (14.5) * cell, (7.5) * cell, 'LEFT', LUDO_COLORS.blue, cell);
    drawArrow(ctx, (7.5) * cell, (0.5) * cell, 'DOWN', LUDO_COLORS.yellow, cell);
    drawArrow(ctx, (0.5) * cell, (7.5) * cell, 'RIGHT', LUDO_COLORS.green, cell);

    // Group Occupants per Cell for Stacked Offsets
    const cellOccupants = {};
    state.players.forEach(p => {
        p.tokens.forEach(token => {
            let key = '';
            if (token.state === 'YARD') key = `YARD_${p.seat_index}_${token.id}`;
            else if (token.state === 'HOME') key = `HOME_${p.seat_index}_${token.id}`;
            else {
                const posCoords = getStandardGridCoords(p.seat_index, token.state, token.pos);
                key = `${posCoords.r}_${posCoords.c}`;
            }
            if (!cellOccupants[key]) cellOccupants[key] = [];
            cellOccupants[key].push({ player: p, token: token });
        });
    });

    const validTokenIds = (validMovesInfo && validMovesInfo.valid_token_ids) ? validMovesInfo.valid_token_ids : [];
    const pulsingScale = 1 + Math.sin(Date.now() / 150) * 0.12;

    state.players.forEach(p => {
        const yardInfo = yards[p.seat_index % 4];
        const circs = [
            { r: yardInfo.r + 1.8, c: yardInfo.c + 1.8 },
            { r: yardInfo.r + 1.8, c: yardInfo.c + 4.2 },
            { r: yardInfo.r + 4.2, c: yardInfo.c + 1.8 },
            { r: yardInfo.r + 4.2, c: yardInfo.c + 4.2 }
        ];

        p.tokens.forEach((token, tIdx) => {
            let tx = 0, ty = 0;

            if (token.state === 'YARD') {
                tx = circs[tIdx].c * cell;
                ty = circs[tIdx].r * cell;
            } else if (token.state === 'HOME') {
                tx = cx + (tIdx - 1.5) * 10;
                ty = cy + (tIdx - 1.5) * 10;
            } else {
                const gridPos = getStandardGridCoords(p.seat_index, token.state, token.pos);
                tx = (gridPos.c + 0.5) * cell;
                ty = (gridPos.r + 0.5) * cell;

                // Stack offset if multiple tokens on same cell
                const key = `${gridPos.r}_${gridPos.c}`;
                const occupants = cellOccupants[key] || [];
                if (occupants.length > 1) {
                    const stackIdx = occupants.findIndex(item => item.player.id === p.id && item.token.id === token.id);
                    if (stackIdx >= 0) {
                        const angle = (stackIdx * 2 * Math.PI) / occupants.length;
                        const offsetR = cell * 0.18;
                        tx += Math.cos(angle) * offsetR;
                        ty += Math.sin(angle) * offsetR;
                    }
                }
            }

            const isSelectable = (state.current_player_index === p.id && validTokenIds.includes(token.id) && p.id === clientSeatIndex);
            const tokenRadius = isSelectable ? (cell * 0.42 * pulsingScale) : (cell * 0.35);

            // Token Drop Shadow
            ctx.beginPath();
            ctx.arc(tx + 2, ty + 3, tokenRadius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
            ctx.fill();

            // Outer Token Body
            ctx.beginPath();
            ctx.arc(tx, ty, tokenRadius, 0, Math.PI * 2);
            ctx.fillStyle = getColorHex(p.color);
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = isSelectable ? 3 : 2;
            ctx.stroke();

            // Inner Ring Highlight
            ctx.beginPath();
            ctx.arc(tx, ty, tokenRadius * 0.55, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
            ctx.fill();

            // Glowing Bouncing Ring for Legal Moves
            if (isSelectable) {
                ctx.beginPath();
                ctx.arc(tx, ty, tokenRadius * 1.4, 0, Math.PI * 2);
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 3.5;
                ctx.stroke();
            }

            tokenClickTargets.push({
                tokenId: token.id,
                x: tx,
                y: ty,
                radius: cell * 0.6,
                isSelectable: isSelectable
            });
        });
    });

    if (validTokenIds.length > 0) {
        requestAnimationFrame(() => renderLudoBoard(state, validMovesInfo));
    }
}

function renderPolygonalLudo(ctx, cx, cy, width, height, totalArms, state, validMovesInfo, tokenClickTargets) {
    const outerR = Math.min(width, height) / 2 - 40;
    const innerR = 70;

    ctx.beginPath();
    for (let i = 0; i < totalArms; i++) {
        const a = (i * 2 * Math.PI) / totalArms - Math.PI / 2;
        const px = cx + Math.cos(a) * innerR;
        const py = cy + Math.sin(a) * innerR;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = '#0f172a';
    ctx.fill();
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 16px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('HOME 🏆', cx, cy);

    const validTokenIds = (validMovesInfo && validMovesInfo.valid_token_ids) ? validMovesInfo.valid_token_ids : [];

    state.players.forEach(p => {
        const angle = (p.seat_index * 2 * Math.PI) / totalArms - Math.PI / 2;
        const yardX = cx + Math.cos(angle) * outerR;
        const yardY = cy + Math.sin(angle) * outerR;

        ctx.beginPath();
        ctx.arc(yardX, yardY, 36, 0, Math.PI * 2);
        ctx.fillStyle = getColorHex(p.color);
        ctx.globalAlpha = 0.3;
        ctx.fill();
        ctx.globalAlpha = 1.0;
        ctx.strokeStyle = getColorHex(p.color);
        ctx.lineWidth = 3;
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px Outfit, sans-serif';
        ctx.fillText(p.name, yardX, yardY - 44);

        ctx.beginPath();
        ctx.moveTo(yardX, yardY);
        ctx.lineTo(cx + Math.cos(angle) * innerR, cy + Math.sin(angle) * innerR);
        ctx.strokeStyle = getColorHex(p.color);
        ctx.lineWidth = 5;
        ctx.stroke();

        p.tokens.forEach((token, tIdx) => {
            const offsetAngle = (tIdx * Math.PI / 2);
            let tx = yardX + Math.cos(offsetAngle) * 16;
            let ty = yardY + Math.sin(offsetAngle) * 16;

            if (token.state === 'TRACK') {
                const stepAngle = ((p.seat_index * 6 + token.pos) * 2 * Math.PI) / state.total_circuit_length - Math.PI / 2;
                const trackR = innerR + 65;
                tx = cx + Math.cos(stepAngle) * trackR;
                ty = cy + Math.sin(stepAngle) * trackR;
            } else if (token.state === 'STRETCH') {
                const prog = (token.pos + 1) / state.arm_length;
                tx = yardX + (cx - yardX) * prog;
                ty = yardY + (cy - yardY) * prog;
            } else if (token.state === 'HOME') {
                tx = cx + (tIdx - 1.5) * 10;
                ty = cy + (tIdx - 1.5) * 10;
            }

            const isSelectable = (state.current_player_index === p.id && validTokenIds.includes(token.id) && p.id === clientSeatIndex);

            ctx.beginPath();
            ctx.arc(tx, ty, isSelectable ? 14 : 10, 0, Math.PI * 2);
            ctx.fillStyle = getColorHex(p.color);
            ctx.fill();
            ctx.strokeStyle = isSelectable ? '#fbbf24' : '#ffffff';
            ctx.lineWidth = isSelectable ? 3 : 1.5;
            ctx.stroke();

            if (isSelectable) {
                ctx.beginPath();
                ctx.arc(tx, ty, 18, 0, Math.PI * 2);
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            tokenClickTargets.push({
                tokenId: token.id,
                x: tx,
                y: ty,
                radius: 18,
                isSelectable: isSelectable
            });
        });
    });
}

function drawTriangle(ctx, x1, y1, x2, y2, x3, y3, color) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.lineTo(x3, y3);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
}

function drawSafeSquare(ctx, c, r, cell, color) {
    ctx.fillStyle = color;
    ctx.fillRect(c * cell, r * cell, cell, cell);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1;
    ctx.strokeRect(c * cell, r * cell, cell, cell);
    drawShieldStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.38, '#ffffff');
}

function drawShieldStar(ctx, cx, cy, r, color) {
    ctx.save();
    ctx.beginPath();
    ctx.fillStyle = color;
    for (let i = 0; i < 5; i++) {
        ctx.lineTo(cx + Math.cos((18 + i * 72) * Math.PI / 180) * r, cy - Math.sin((18 + i * 72) * Math.PI / 180) * r);
        ctx.lineTo(cx + Math.cos((54 + i * 72) * Math.PI / 180) * (r / 2), cy - Math.sin((54 + i * 72) * Math.PI / 180) * (r / 2));
    }
    ctx.closePath();
    ctx.fill();
    ctx.restore();
}

function drawArrow(ctx, cx, cy, dir, color, cell) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.font = `bold ${cell * 0.7}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const arrowChar = dir === 'UP' ? '⬆' : dir === 'DOWN' ? '⬇' : dir === 'LEFT' ? '⬅' : '➔';
    ctx.fillText(arrowChar, cx, cy);
    ctx.restore();
}

function sendQuickPhrase(phrase) {
    playLudoSound('phrase');
    showQuickPhraseBubble(phrase);
    if (typeof socket !== 'undefined' && socket) {
        socket.send(jsonPayload('game_action', { type: 'quick_phrase', phrase: phrase }));
    }
}

function showQuickPhraseBubble(phrase, senderName = 'You') {
    const overlay = document.getElementById('reactionOverlay');
    if (!overlay) return;

    const bubble = document.createElement('div');
    bubble.className = 'speech-bubble bg-slate-800/90 text-white font-bold text-xs px-3 py-1.5 rounded-2xl border border-slate-600 shadow-xl flex items-center space-x-1.5 z-30';
    bubble.innerHTML = `<span>💬</span><span>${senderName}: "${phrase}"</span>`;
    overlay.appendChild(bubble);

    setTimeout(() => {
        bubble.classList.add('opacity-0', 'scale-90');
        setTimeout(() => bubble.remove(), 400);
    }, 2500);
}
