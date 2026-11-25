/* =========================================================
   MegiLoka JavaScript Interactive Module
   ========================================================= */

document.addEventListener('DOMContentLoaded', function () {
    // Dynamic price calculation on POS & Booking page
    const ticketInputs = document.querySelectorAll('.ticket-qty-input');
    if (ticketInputs.length > 0) {
        ticketInputs.forEach(input => {
            input.addEventListener('input', calculateTotalPrice);
        });
        calculateTotalPrice();
    }

    const visitDate = document.getElementById('bookingVisitDate');
    if (visitDate) {
        const updateBookingRates = () => {
            const weekday = (new Date(visitDate.value + 'T00:00:00Z').getUTCDay() + 6) % 7;
            let hasRates = false;
            document.querySelectorAll('.ticket-type-row[data-weekdays]').forEach(row => {
                const offered = Boolean(visitDate.value && (Number(row.dataset.weekdays) & (1 << weekday)));
                const input = row.querySelector('.ticket-qty-input');
                row.hidden = !offered;
                input.disabled = !offered;
                if (!offered) input.value = '0';
                hasRates ||= offered;
            });
            document.getElementById('noBookingRates').hidden = hasRates;
            document.getElementById('bookingSubmit').disabled = !hasRates;
            calculateTotalPrice();
        };
        visitDate.addEventListener('change', updateBookingRates);
        updateBookingRates();
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
    let subtotalCents = 0;
    let ticketCount = 0;
    const ticketRows = document.querySelectorAll('.ticket-type-row');

    ticketRows.forEach(row => {
        const price = parseFloat(row.dataset.price || 0);
        const qtyInput = row.querySelector('.ticket-qty-input');
        const subtotalEl = row.querySelector('.subtotal-amount');

        if (qtyInput && !qtyInput.disabled) {
            const qty = Math.max(0, Number.parseInt(qtyInput.value, 10) || 0);
            const lineCents = Math.round(price * 100) * qty;
            subtotalCents += lineCents;
            ticketCount += qty;

            if (subtotalEl) {
                subtotalEl.textContent = formatRupiah(lineCents / 100);
            }
        }
    });

    const grandTotalEl = document.getElementById('grandTotalDisplay');
    const totalAmountInput = document.getElementById('totalAmountInput');

    if (!grandTotalEl) return;
    const minimum = Number(grandTotalEl.dataset.quantityMinimum);
    const percent = Number(grandTotalEl.dataset.quantityPercent);
    const discount = ticketCount >= minimum ? Math.round(subtotalCents * percent / 10000) : 0;
    const grandTotal = (subtotalCents - discount * 100) / 100;
    grandTotalEl.textContent = formatRupiah(grandTotal);

    const discountLine = document.getElementById('quantityDiscountLine');
    if (discountLine) {
        discountLine.hidden = discount === 0;
        document.getElementById('quantityDiscountAmount').textContent = formatRupiah(discount);
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

        if (data.action_executed === 'add_event' || data.action_executed === 'add_destination') {
            playBeepSound('success');
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
