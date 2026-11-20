/* =========================================================
   MegiLoka JavaScript Interactive Module
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {
    // Dynamic price calculation on POS & Booking page
    const ticketInputs = document.querySelectorAll('.ticket-qty-input');
    if (ticketInputs.length > 0) {
        ticketInputs.forEach(input => {
            input.addEventListener('change', calculateTotalPrice);
            input.addEventListener('keyup', calculateTotalPrice);
        });
        calculateTotalPrice();
    }

    // Auto dismiss alert notifications after 5s
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    const holidayFeed = document.getElementById('holiday-feed-content');
    if (holidayFeed) {
        let loading = false;
        const refresh = async () => {
            if (document.hidden || loading) return;
            loading = true;
            try {
                const response = await fetch(holidayFeed.dataset.url, {cache: 'no-store'});
                if (!response.ok) return;
                const markup = await response.text();
                if (markup.trim() !== holidayFeed.innerHTML.trim() && !holidayFeed.contains(document.activeElement)) {
                    holidayFeed.innerHTML = markup;
                }
            } catch (error) {
                console.warn('Pembaruan agenda libur belum tersedia.', error);
            } finally {
                loading = false;
            }
        };
        setInterval(refresh, 30000);
        document.addEventListener('visibilitychange', refresh);
    }
});

function calculateTotalPrice() {
    let grandTotal = 0;
    const ticketRows = document.querySelectorAll('.ticket-type-row');

    ticketRows.forEach(row => {
        const price = parseFloat(row.dataset.price || 0);
        const qtyInput = row.querySelector('.ticket-qty-input');
        const subtotalEl = row.querySelector('.subtotal-amount');

        if (qtyInput) {
            const qty = parseInt(qtyInput.value) || 0;
            const subtotal = price * qty;
            grandTotal += subtotal;

            if (subtotalEl) {
                subtotalEl.textContent = formatRupiah(subtotal);
            }
        }
    });

    const grandTotalEl = document.getElementById('grandTotalDisplay');
    const totalAmountInput = document.getElementById('totalAmountInput');

    if (grandTotalEl) {
        grandTotalEl.textContent = formatRupiah(grandTotal);
    }
    if (totalAmountInput) {
        totalAmountInput.value = grandTotal;
    }
}

function formatRupiah(amount) {
    return 'Rp ' + new Intl.NumberFormat('id-ID').format(amount);
}

// Audio Feedback Generator for Scanner (Beep sound on scan)
function playBeepSound(type = 'success') {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (type === 'success') {
            osc.frequency.value = 880; // High beep A5
            gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.15);
        } else {
            osc.frequency.value = 220; // Low beep A3 error
            gain.gain.setValueAtTime(0.4, audioCtx.currentTime);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.35);
        }
    } catch (e) {
        console.log('Audio Context unsupported or muted:', e);
    }
}

// =========================================================
// MegiBot AI Concierge & Notification Center Scripts
// =========================================================

function toggleMegiBot() {
    const panel = document.getElementById('megibot-panel');
    if (!panel) return;

    if (panel.classList.contains('d-none')) {
        panel.classList.remove('d-none');
        document.getElementById('megibot-input')?.focus();
    } else {
        panel.classList.add('d-none');
    }
}

let megiRequestPending = false;

async function askMegi(question) {
    if (megiRequestPending) return;
    const panel = document.getElementById('megibot-panel');
    if (panel && panel.classList.contains('d-none')) {
        panel.classList.remove('d-none');
    }

    appendChatMessage(question, 'user');
    await sendAiRequest({ message: question });
}

async function handleMegiBotSubmit(e) {
    e.preventDefault();
    if (megiRequestPending) return;
    const input = document.getElementById('megibot-input');
    const msg = input.value.trim();
    if (!msg) return;

    appendChatMessage(msg, 'user');
    input.value = '';

    await sendAiRequest({ message: msg });
}

function escapeChatText(text) {
    return String(text).replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[char]));
}

function appendChatMessage(text, sender = 'bot', sources = []) {
    const container = document.getElementById('megibot-messages');
    if (!container) return;

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender === 'user' ? 'user-bubble' : 'bot-bubble shadow-sm border'} mb-3 p-3`;

    if (sender === 'bot') {
        // Format basic markdown bolding, code & newlines
        const formatted = escapeChatText(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code class="bg-light text-danger px-1 py-0 rounded">$1</code>')
            .replace(/\n/g, '<br>');

        bubble.innerHTML = `
            <div class="d-flex align-items-center gap-1 mb-1 text-primary fw-bold small">
                <i class="fa-solid fa-robot"></i> Tanya Megi
            </div>
            <div class="small text-dark">${formatted}</div>
        `;
    } else {
        bubble.innerHTML = `<div class="small">${escapeChatText(text).replace(/\n/g, '<br>')}</div>`;
    }

    if (sender === 'bot' && Array.isArray(sources) && sources.length) {
        const links = document.createElement('div');
        links.className = 'd-flex flex-wrap gap-1 mt-2';
        sources.forEach(source => {
            if (!source || typeof source.url !== 'string' || !/^\/(?:#agenda-libur|calendar|destinations(?:\/\d+)?|booking\/\d+)$/.test(source.url)) return;
            const link = document.createElement('a');
            link.className = 'btn btn-sm btn-outline-primary text-start';
            link.href = source.url;
            link.textContent = source.label || 'Lihat sumber';
            links.appendChild(link);
        });
        bubble.appendChild(links);
    }

    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

async function sendAiRequest(payload) {
    if (megiRequestPending) return;
    megiRequestPending = true;
    const container = document.getElementById('megibot-messages');
    const sendBtn = document.getElementById('megibot-send-btn');

    // Typing indicator
    const typingBubble = document.createElement('div');
    typingBubble.id = 'ai-typing-indicator';
    typingBubble.className = 'chat-bubble bot-bubble shadow-sm border mb-3 p-2 px-3 text-muted small d-flex align-items-center gap-2';
    typingBubble.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin text-primary"></i> Megi sedang memproses data...';
    container.appendChild(typingBubble);
    container.scrollTop = container.scrollHeight;

    if (sendBtn) sendBtn.disabled = true;

    try {
        const res = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        typingBubble.remove();

        if (data.reply) {
            appendChatMessage(data.reply, 'bot', data.sources);
        }

        // If an item was added, refresh notifications & spotlight section
        if (data.action_executed === 'add_event' || data.action_executed === 'add_destination') {
            playBeepSound('success');
            await refreshGuestNotifications();

            // Reload page if on home so spotlight section displays immediately
            if (window.location.pathname === '/' || window.location.pathname === '') {
                setTimeout(() => {
                    window.location.reload();
                }, 2200);
            }
        }
    } catch (err) {
        typingBubble.remove();
        appendChatMessage('Mohon maaf, terjadi kendala saat menghubungi server Tanya Megi. Silakan coba kembali.', 'bot');
        console.error(err);
    } finally {
        megiRequestPending = false;
        if (sendBtn) sendBtn.disabled = false;
    }
}

async function refreshGuestNotifications() {
    try {
        const res = await fetch('/api/guest/notifications');
        const data = await res.json();
        if (!data.success) return;

        const countBadge = document.getElementById('notifBadgeCount');
        const countHeader = document.getElementById('notifCountHeader');
        const toastCountBadge = document.getElementById('toastCountBadge');
        const toastBodyText = document.getElementById('toastBodyText');
        const container = document.getElementById('notifListContainer');

        if (countBadge) {
            countBadge.textContent = data.total;
            if (data.total > 0) {
                countBadge.classList.remove('d-none');
            }
        }
        if (countHeader) {
            countHeader.textContent = `${data.total} Baru`;
        }
        if (toastCountBadge) {
            toastCountBadge.textContent = `${data.total} Agenda`;
        }
        if (toastBodyText) {
            toastBodyText.innerHTML = `Ada <strong>${data.total} agenda wisata/destinasi</strong> yang akan berlangsung <strong>besok (H-1)</strong> atau dalam <strong>1 bulan ke depan</strong>!`;
        }

        if (container && data.notifications.length > 0) {
            let html = '';
            data.notifications.forEach(n => {
                html += `
                    <a href="${n.url}" class="dropdown-item p-2 mb-1 rounded-3 text-wrap border-bottom text-decoration-none ${n.is_urgent ? 'bg-warning-subtle border-warning-subtle' : 'bg-light'}">
                        <div class="d-flex align-items-center justify-content-between mb-1">
                            <span class="badge ${n.badge_class} rounded-pill font-monospace" style="font-size: 0.7rem;">${n.badge_label}</span>
                            <small class="text-muted" style="font-size: 0.7rem;">${n.timing_desc}</small>
                        </div>
                        <div class="fw-bold text-dark small mb-1">${n.title}</div>
                        <div class="text-muted" style="font-size: 0.72rem;">
                            <i class="fa-solid fa-location-dot me-1 text-primary"></i>${n.location} • ${n.date_str}
                        </div>
                    </a>
                `;
            });
            container.innerHTML = html;
        }
    } catch (e) {
        console.error('Failed refreshing guest notifications:', e);
    }
}
