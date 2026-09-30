// Studio D-Art - Interactive Motion & Application Logic (Squarespace Inspired)

document.addEventListener('DOMContentLoaded', function () {
    initScrollReveals();
    initAnimatedCounters();
    initSpotlightAndTilt();
    initCategoryPillsFilter();
    initQuickViewModal();
    initCommissionCalculator();
    initAmbientParticleCanvas();
    initSeatReservationModal();
    initAutoDismissAlerts();
});

/* -------------------------------------------------------------
 * 1. Scroll Reveal Animations (IntersectionObserver)
 * ------------------------------------------------------------- */
function initScrollReveals() {
    const revealElements = document.querySelectorAll('.reveal-on-scroll');
    if (!revealElements.length) return;

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-revealed');
                obs.unobserve(entry.target); // Reveal once
            }
        });
    }, {
        threshold: 0.15,
        rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach(el => observer.observe(el));
}

/* -------------------------------------------------------------
 * 2. Animated Number Counters
 * ------------------------------------------------------------- */
function initAnimatedCounters() {
    const counters = document.querySelectorAll('[data-counter-target]');
    if (!counters.length) return;

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(entry.target.getAttribute('data-counter-target'), 10);
                const suffix = entry.target.getAttribute('data-counter-suffix') || '';
                animateValue(entry.target, 0, target, 1500, suffix);
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(counter => observer.observe(counter));
}

function animateValue(element, start, end, duration, suffix) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const easeProgress = 1 - Math.pow(1 - progress, 3); // cubic ease-out
        const current = Math.floor(easeProgress * (end - start) + start);
        element.textContent = current + suffix;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

/* -------------------------------------------------------------
 * 3. 3D Card Tilt & Cursor Spotlight Effects
 * ------------------------------------------------------------- */
function initSpotlightAndTilt() {
    const cards = document.querySelectorAll('.spotlight-card, .art-card, .glass-panel');

    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);

            if (card.classList.contains('tilt-card')) {
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const rotateX = ((y - centerY) / centerY) * -6; // max 6deg
                const rotateY = ((x - centerX) / centerX) * 6;
                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-6px)`;
            }
        });

        card.addEventListener('mouseleave', () => {
            if (card.classList.contains('tilt-card')) {
                card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
            }
        });
    });
}

/* -------------------------------------------------------------
 * 4. Interactive Category Pill Filter (Instant Card Filter)
 * ------------------------------------------------------------- */
function initCategoryPillsFilter() {
    const pills = document.querySelectorAll('.filter-pill');
    const artCards = document.querySelectorAll('.filterable-art-card');
    if (!pills.length || !artCards.length) return;

    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            pills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const selectedCategory = pill.getAttribute('data-filter');

            artCards.forEach(card => {
                const medium = card.getAttribute('data-medium') || '';

                if (selectedCategory === 'all' || medium.toLowerCase().includes(selectedCategory.toLowerCase())) {
                    card.style.display = '';
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'scale(1)';
                    }, 50);
                } else {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.92)';
                    setTimeout(() => {
                        card.style.display = 'none';
                    }, 300);
                }
            });
        });
    });
}

/* -------------------------------------------------------------
 * 5. Interactive Artwork Quick View Modal
 * ------------------------------------------------------------- */
function initQuickViewModal() {
    const quickViewButtons = document.querySelectorAll('.quickview-btn');
    const modalEl = document.getElementById('quickViewModal');
    if (!quickViewButtons.length || !modalEl) return;

    quickViewButtons.forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            e.stopPropagation();

            const title = btn.getAttribute('data-title');
            const medium = btn.getAttribute('data-medium');
            const dimensions = btn.getAttribute('data-dimensions');
            const price = btn.getAttribute('data-price');
            const img = btn.getAttribute('data-img');
            const desc = btn.getAttribute('data-desc');
            const slug = btn.getAttribute('data-slug');
            const isAvailable = btn.getAttribute('data-available') === 'true';

            document.getElementById('qvModalTitle').textContent = title;
            document.getElementById('qvModalMedium').textContent = medium;
            document.getElementById('qvModalDimensions').textContent = dimensions;
            document.getElementById('qvModalPrice').textContent = 'Rs ' + price;
            document.getElementById('qvModalImage').src = img;
            document.getElementById('qvModalDesc').textContent = desc;

            const availBadge = document.getElementById('qvModalAvailability');
            if (isAvailable) {
                availBadge.className = 'badge badge-available px-3 py-2 fs-6';
                availBadge.innerHTML = '<i class="bi bi-circle-fill me-1 small"></i> Available for Acquisition';
            } else {
                availBadge.className = 'badge badge-sold px-3 py-2 fs-6';
                availBadge.innerHTML = '<i class="bi bi-lock-fill me-1"></i> Private Collection';
            }

            const detailBtn = document.getElementById('qvModalDetailBtn');
            if (detailBtn && slug) {
                detailBtn.href = `/artwork/${slug}/`;
            }

            const inquireBtn = document.getElementById('qvModalInquireBtn');
            if (inquireBtn) {
                inquireBtn.href = `/contact/?subject=Inquiry regarding: ${encodeURIComponent(title)}`;
            }

            const bsModal = new bootstrap.Modal(modalEl);
            bsModal.show();
        });
    });
}

/* -------------------------------------------------------------
 * 6. Interactive Commission Price & Size Calculator
 * ------------------------------------------------------------- */
function initCommissionCalculator() {
    const widthInput = document.getElementById('calcWidth');
    const heightInput = document.getElementById('calcHeight');
    const mediumSelect = document.getElementById('calcMedium');
    const frameSelect = document.getElementById('calcFrame');

    if (!widthInput || !heightInput || !mediumSelect) return;

    const widthVal = document.getElementById('calcWidthVal');
    const heightVal = document.getElementById('calcHeightVal');
    const livePriceSpan = document.getElementById('calcLivePrice');
    const prefillBtn = document.getElementById('calcPrefillBtn');

    function calculatePrice() {
        const w = parseInt(widthInput.value, 10);
        const h = parseInt(heightInput.value, 10);
        const mediumMultiplier = parseFloat(mediumSelect.value) || 1.0;
        const frameAddon = parseFloat(frameSelect ? frameSelect.value : 0) || 0;

        if (widthVal) widthVal.textContent = w + '"';
        if (heightVal) heightVal.textContent = h + '"';

        const sqInches = w * h;
        // Base rate ~ Rs 25 per sq inch + medium complexity + framing
        let estimatedPrice = (sqInches * 25 * mediumMultiplier) + frameAddon;
        estimatedPrice = Math.round(estimatedPrice / 500) * 500; // Round to nearest 500

        if (livePriceSpan) {
            livePriceSpan.textContent = 'Rs ' + estimatedPrice.toLocaleString('en-IN');
        }

        if (prefillBtn) {
            const mediumText = mediumSelect.options[mediumSelect.selectedIndex].text;
            prefillBtn.href = `/commission/?style=${encodeURIComponent(mediumText)}&dimensions=${w}x${h}&est=${estimatedPrice}`;
        }
    }

    [widthInput, heightInput, mediumSelect, frameSelect].forEach(input => {
        if (input) input.addEventListener('input', calculatePrice);
    });

    calculatePrice();
}

/* -------------------------------------------------------------
 * 7. Studio Ambient Particle Canvas (Golden Dust Effect)
 * ------------------------------------------------------------- */
function initAmbientParticleCanvas() {
    const toggleBtn = document.getElementById('ambientGlowToggle');
    if (!toggleBtn) return;

    let canvas = document.getElementById('studioAmbientCanvas');
    if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'studioAmbientCanvas';
        document.body.appendChild(canvas);
    }

    const ctx = canvas.getContext('2d');
    let particles = [];
    let animationId = null;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2.5 + 0.5;
            this.speedY = Math.random() * -0.4 - 0.1;
            this.speedX = Math.random() * 0.4 - 0.2;
            this.opacity = Math.random() * 0.6 + 0.2;
        }
        update() {
            this.y += this.speedY;
            this.x += this.speedX;
            if (this.y < -10 || this.x < -10 || this.x > canvas.width + 10) {
                this.reset();
                this.y = canvas.height + 10;
            }
        }
        draw() {
            ctx.fillStyle = `rgba(212, 175, 55, ${this.opacity})`;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    for (let i = 0; i < 45; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        animationId = requestAnimationFrame(animate);
    }

    toggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('ambient-mode');
        const isActive = document.body.classList.contains('ambient-mode');
        toggleBtn.classList.toggle('active', isActive);

        if (isActive) {
            toggleBtn.innerHTML = '<i class="bi bi-sparkles me-1"></i> Studio Glow: ON';
            animate();
        } else {
            toggleBtn.innerHTML = '<i class="bi bi-moon-stars me-1"></i> Studio Glow: OFF';
            if (animationId) cancelAnimationFrame(animationId);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    });
}

/* -------------------------------------------------------------
 * 8. Seat Reservation Modal Helper
 * ------------------------------------------------------------- */
function initSeatReservationModal() {
    const reserveModal = document.getElementById('reserveSeatModal');
    if (!reserveModal) return;

    reserveModal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        if (button) {
            const classId = button.getAttribute('data-class-id');
            const classTitle = button.getAttribute('data-class-title');
            const classPrice = button.getAttribute('data-class-price');
            const seatsAvailable = button.getAttribute('data-seats-available');

            const modalClassIdInput = reserveModal.querySelector('#id_class_id');
            const modalTitleSpan = reserveModal.querySelector('#modalClassTitle');
            const modalPriceSpan = reserveModal.querySelector('#modalClassPrice');
            const modalSeatsInput = reserveModal.querySelector('#id_seats_count');

            if (modalClassIdInput) modalClassIdInput.value = classId;
            if (modalTitleSpan) modalTitleSpan.textContent = classTitle;
            if (modalPriceSpan) modalPriceSpan.textContent = 'Rs ' + classPrice;
            if (modalSeatsInput && seatsAvailable) {
                modalSeatsInput.setAttribute('max', seatsAvailable);
            }
        }
    });
}

/* -------------------------------------------------------------
 * 9. Auto Dismiss Alerts
 * ------------------------------------------------------------- */
function initAutoDismissAlerts() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });
}
