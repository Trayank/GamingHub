// ludo_render.js - Parametric Polygonal Board Generator (SVG/Canvas) for 2-10 Players Ludo

function renderLudoBoard(state, validMovesInfo) {
    const canvas = document.getElementById('gameBoardCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const width = canvas.width;
    const height = canvas.height;
    const cx = width / 2;
    const cy = height / 2;

    ctx.clearRect(0, 0, width, height);

    // Background fill
    ctx.fillStyle = '#090d16';
    ctx.fillRect(0, 0, width, height);

    const playerCount = state.player_count || 4;
    const totalArms = state.total_arms || playerCount;
    const players = state.players || [];
    const validTokenIds = (validMovesInfo && validMovesInfo.valid_token_ids) ? validMovesInfo.valid_token_ids : [];
    const movePreviews = (validMovesInfo && validMovesInfo.move_previews) ? validMovesInfo.move_previews : {};

    const tokenClickTargets = [];

    if (totalArms === 4) {
        // Standard 15x15 Cross Layout for 2-4 players
        renderStandard4QuadrantLudo(ctx, width, height, state, validMovesInfo, tokenClickTargets);
    } else {
        // Parametric Polygonal Layout (Hexagonal: 5-6, Octagonal: 7-8, Decagonal: 9-10)
        renderPolygonalLudo(ctx, cx, cy, width, height, totalArms, state, validMovesInfo, tokenClickTargets);
    }

    // Canvas Click Handler
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

function renderStandard4QuadrantLudo(ctx, width, height, state, validMovesInfo, tokenClickTargets) {
    const size = Math.min(width, height);
    const grid = 15;
    const cell = size / grid;

    const COLORS = {
        0: { fill: '#ef4444', name: 'red' },    // Top-Left / Red
        1: { fill: '#3b82f6', name: 'blue' },   // Top-Right / Blue
        2: { fill: '#eab308', name: 'yellow' }, // Bottom-Right / Yellow
        3: { fill: '#10b981', name: 'green' }   // Bottom-Left / Green
    };

    // Draw Outer Board Border
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 4;
    ctx.strokeRect(0, 0, size, size);

    // Draw 4 Corner Base Yards (6x6 cells each)
    const yards = [
        { r: 0, c: 0, seat: 0, color: '#ef4444' }, // Red Top-Left
        { r: 0, c: 9, seat: 1, color: '#3b82f6' }, // Blue Top-Right
        { r: 9, c: 9, seat: 2, color: '#eab308' }, // Yellow Bottom-Right
        { r: 9, c: 0, seat: 3, color: '#10b981' }  // Green Bottom-Left
    ];

    yards.forEach(y => {
        ctx.fillStyle = y.color;
        ctx.fillRect(y.c * cell, y.r * cell, 6 * cell, 6 * cell);

        // White inner yard box
        ctx.fillStyle = '#ffffff';
        ctx.fillRect((y.c + 1) * cell, (y.r + 1) * cell, 4 * cell, 4 * cell);

        // 4 Yard Circle Token Holders
        const circles = [
            { r: y.r + 1.8, c: y.c + 1.8 },
            { r: y.r + 1.8, c: y.c + 3.2 },
            { r: y.r + 3.2, c: y.c + 1.8 },
            { r: y.r + 3.2, c: y.c + 3.2 }
        ];

        circles.forEach(circ => {
            ctx.beginPath();
            ctx.arc(circ.c * cell, circ.r * cell, cell * 0.5, 0, Math.PI * 2);
            ctx.fillStyle = y.color;
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();
        });
    });

    // Draw Center Home Triangle Zone (3x3 grid cells: 6..8, 6..8)
    const cx = 7.5 * cell;
    const cy = 7.5 * cell;

    ctx.fillStyle = '#1e293b';
    ctx.fillRect(6 * cell, 6 * cell, 3 * cell, 3 * cell);

    // Center triangles
    drawTriangle(ctx, 6 * cell, 6 * cell, 6 * cell, 9 * cell, cx, cy, '#ef4444');
    drawTriangle(ctx, 6 * cell, 6 * cell, 9 * cell, 6 * cell, cx, cy, '#3b82f6');
    drawTriangle(ctx, 9 * cell, 6 * cell, 9 * cell, 9 * cell, cx, cy, '#eab308');
    drawTriangle(ctx, 6 * cell, 9 * cell, 9 * cell, 9 * cell, cx, cy, '#10b981');

    // Draw Grid Track Cells (3x6 tracks)
    for (let r = 0; r < 15; r++) {
        for (let c = 0; c < 15; c++) {
            const isYard = (r < 6 && c < 6) || (r < 6 && c > 8) || (r > 8 && c < 6) || (r > 8 && c > 8);
            const isCenter = (r >= 6 && r <= 8 && c >= 6 && c <= 8);

            if (!isYard && !isCenter) {
                ctx.strokeStyle = '#475569';
                ctx.lineWidth = 1;
                ctx.strokeRect(c * cell, r * cell, cell, cell);

                // Home Stretch Colors
                if (c === 7 && r >= 1 && r <= 5) { ctx.fillStyle = '#ef4444'; ctx.fillRect(c * cell, r * cell, cell, cell); }
                if (r === 7 && c >= 9 && c <= 13) { ctx.fillStyle = '#3b82f6'; ctx.fillRect(c * cell, r * cell, cell, cell); }
                if (c === 7 && r >= 9 && r <= 13) { ctx.fillStyle = '#eab308'; ctx.fillRect(c * cell, r * cell, cell, cell); }
                if (r === 7 && c >= 1 && c <= 5) { ctx.fillStyle = '#10b981'; ctx.fillRect(c * cell, r * cell, cell, cell); }

                // Safe Start Spots (Colored)
                if (r === 1 && c === 6) drawSafeSquare(ctx, c, r, cell, '#ef4444');
                if (r === 6 && c === 13) drawSafeSquare(ctx, c, r, cell, '#3b82f6');
                if (r === 13 && c === 8) drawSafeSquare(ctx, c, r, cell, '#eab308');
                if (r === 8 && c === 1) drawSafeSquare(ctx, c, r, cell, '#10b981');

                // Intermediate Star Safe Spots
                if (r === 2 && c === 8) drawStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.35, '#f59e0b');
                if (r === 8 && c === 12) drawStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.35, '#f59e0b');
                if (r === 12 && c === 6) drawStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.35, '#f59e0b');
                if (r === 6 && c === 2) drawStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.35, '#f59e0b');
            }
        }
    }

    // Render Player Tokens
    const validTokenIds = (validMovesInfo && validMovesInfo.valid_token_ids) ? validMovesInfo.valid_token_ids : [];

    state.players.forEach(p => {
        const yardInfo = yards[p.seat_index % 4];
        const circs = [
            { r: yardInfo.r + 1.8, c: yardInfo.c + 1.8 },
            { r: yardInfo.r + 1.8, c: yardInfo.c + 3.2 },
            { r: yardInfo.r + 3.2, c: yardInfo.c + 1.8 },
            { r: yardInfo.r + 3.2, c: yardInfo.c + 3.2 }
        ];

        p.tokens.forEach((token, tIdx) => {
            let tx = 0, ty = 0;

            if (token.state === 'YARD') {
                tx = circs[tIdx].c * cell;
                ty = circs[tIdx].r * cell;
            } else if (token.state === 'HOME') {
                tx = cx + (tIdx - 1.5) * 8;
                ty = cy + (tIdx - 1.5) * 8;
            } else {
                // Calculate cell grid position from relative pos
                const gridPos = getStandardGridCoords(p.seat_index, token.state, token.pos);
                tx = (gridPos.c + 0.5) * cell;
                ty = (gridPos.r + 0.5) * cell;
            }

            const isSelectable = (state.current_player_index === p.id && validTokenIds.includes(token.id) && p.id === clientSeatIndex);

            ctx.beginPath();
            ctx.arc(tx, ty, isSelectable ? cell * 0.45 : cell * 0.35, 0, Math.PI * 2);
            ctx.fillStyle = getColorHex(p.color);
            ctx.fill();
            ctx.strokeStyle = isSelectable ? '#fbbf24' : '#ffffff';
            ctx.lineWidth = isSelectable ? 3 : 1.5;
            ctx.stroke();

            if (isSelectable) {
                ctx.beginPath();
                ctx.arc(tx, ty, cell * 0.55, 0, Math.PI * 2);
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            tokenClickTargets.push({
                tokenId: token.id,
                x: tx,
                y: ty,
                radius: cell * 0.55,
                isSelectable: isSelectable
            });
        });
    });
}

function renderPolygonalLudo(ctx, cx, cy, width, height, totalArms, state, validMovesInfo, tokenClickTargets) {
    const outerR = Math.min(width, height) / 2 - 40;
    const innerR = 70;

    // Draw Central Home Polygon
    ctx.beginPath();
    for (let i = 0; i < totalArms; i++) {
        const a = (i * 2 * Math.PI) / totalArms - Math.PI / 2;
        const px = cx + Math.cos(a) * innerR;
        const py = cy + Math.sin(a) * innerR;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fillStyle = '#1e293b';
    ctx.fill();
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 16px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('HOME', cx, cy);

    const validTokenIds = (validMovesInfo && validMovesInfo.valid_token_ids) ? validMovesInfo.valid_token_ids : [];

    // Render Arms & Base Yards
    state.players.forEach(p => {
        const angle = (p.seat_index * 2 * Math.PI) / totalArms - Math.PI / 2;
        const yardX = cx + Math.cos(angle) * outerR;
        const yardY = cy + Math.sin(angle) * outerR;

        // Base Yard Circle
        ctx.beginPath();
        ctx.arc(yardX, yardY, 36, 0, Math.PI * 2);
        ctx.fillStyle = getColorHex(p.color);
        ctx.globalAlpha = 0.25;
        ctx.fill();
        ctx.globalAlpha = 1.0;
        ctx.strokeStyle = getColorHex(p.color);
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px Outfit, sans-serif';
        ctx.fillText(p.name, yardX, yardY - 44);

        // Home Stretch Line
        ctx.beginPath();
        ctx.moveTo(yardX, yardY);
        ctx.lineTo(cx + Math.cos(angle) * innerR, cy + Math.sin(angle) * innerR);
        ctx.strokeStyle = getColorHex(p.color);
        ctx.lineWidth = 4;
        ctx.stroke();

        // Render Tokens
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

function getStandardGridCoords(seatIdx, state, pos) {
    // Mapping for standard 15x15 Ludo track
    const TRACK_COORDS = [
        {r:6, c:1}, {r:6, c:2}, {r:6, c:3}, {r:6, c:4}, {r:6, c:5},
        {r:5, c:6}, {r:4, c:6}, {r:3, c:6}, {r:2, c:6}, {r:1, c:6}, {r:0, c:6},
        {r:0, c:7}, {r:0, c:8},
        {r:1, c:8}, {r:2, c:8}, {r:3, c:8}, {r:4, c:8}, {r:5, c:8},
        {r:6, c:9}, {r:6, c:10}, {r:6, c:11}, {r:6, c:12}, {r:6, c:13}, {r:6, c:14},
        {r:7, c:14}, {r:8, c:14},
        {r:8, c:13}, {r:8, c:12}, {r:8, c:11}, {r:8, c:10}, {r:8, c:9},
        {r:9, c:8}, {r:10, c:8}, {r:11, c:8}, {r:12, c:8}, {r:13, c:8}, {r:14, c:8},
        {r:14, c:7}, {r:14, c:6},
        {r:13, c:6}, {r:12, c:6}, {r:11, c:6}, {r:10, c:6}, {r:9, c:6},
        {r:8, c:5}, {r:8, c:4}, {r:8, c:3}, {r:8, c:2}, {r:8, c:1}, {r:8, c:0},
        {r:7, c:0}, {r:6, c:0}
    ];

    if (state === 'TRACK') {
        const startOffset = [50, 11, 24, 37][seatIdx % 4];
        const absIdx = (startOffset + pos) % TRACK_COORDS.length;
        return TRACK_COORDS[absIdx];
    } else if (state === 'STRETCH') {
        const stretchPaths = [
            [{r:7, c:1}, {r:7, c:2}, {r:7, c:3}, {r:7, c:4}, {r:7, c:5}], // Green
            [{r:1, c:7}, {r:2, c:7}, {r:3, c:7}, {r:4, c:7}, {r:5, c:7}], // Red
            [{r:7, c:13}, {r:7, c:12}, {r:7, c:11}, {r:7, c:10}, {r:7, c:9}], // Blue
            [{r:13, c:7}, {r:12, c:7}, {r:11, c:7}, {r:10, c:7}, {r:9, c:7}]  // Yellow
        ];
        const path = stretchPaths[seatIdx % 4];
        return path[Math.min(pos, path.length - 1)];
    }
    return { r: 7, c: 7 };
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
    ctx.lineWidth = 1;
    ctx.stroke();
}

function drawSafeSquare(ctx, c, r, cell, color) {
    ctx.fillStyle = color;
    ctx.fillRect(c * cell, r * cell, cell, cell);
    drawStar(ctx, (c + 0.5) * cell, (r + 0.5) * cell, cell * 0.35, '#ffffff');
}

function drawStar(ctx, cx, cy, r, color) {
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
