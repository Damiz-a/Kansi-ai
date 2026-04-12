/* ============================================================
   KANSI AI — Main JavaScript
   Gentle interactions & supportive UX for mental health users
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
    initAlertDismiss();
    initSmoothAnimations();
    initTextareaCounter();
    initChatbot();
    initGoogleAuth();
    initBreathingWidget();
    initGentleTooltips();
    initWarmGreeting();
});

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

/* ── Auto-dismiss alerts after 6 seconds ── */
function initAlertDismiss() {
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 600);
        }, 6000);
    });
}

/* ── Intersection Observer for scroll animations ── */
function initSmoothAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.card, .glass, .feature-card, .stat-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(15px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // Add visible class styles
    const style = document.createElement('style');
    style.textContent = '.visible { opacity: 1 !important; transform: translateY(0) !important; }';
    document.head.appendChild(style);
}

/* ── Textarea character counter ── */
function initTextareaCounter() {
    const textarea = document.querySelector('#chat-input') || document.querySelector('textarea[name="text"]');
    if (!textarea) return;

    const counter = document.createElement('div');
    counter.style.cssText = `
        text-align: right;
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-top: 0.35rem;
        transition: color 0.3s ease;
    `;
    textarea.parentNode.appendChild(counter);

    const update = () => {
        const len = textarea.value.length;
        counter.textContent = `${len} character${len !== 1 ? 's' : ''}`;
        counter.style.color = len < 10 ? 'var(--danger)' : 'var(--text-muted)';
    };

    textarea.addEventListener('input', update);
    update();

    // Gentle placeholder rotation
    const placeholders = [
        'Share what is on your mind. This is a safe space.',
        'You can write anything here, no judgement...',
        'How are you feeling today? Express freely.',
        'Your words matter. Type what you are experiencing.',
    ];
    let pIdx = 0;
    setInterval(() => {
        if (!textarea.value && document.activeElement !== textarea) {
            pIdx = (pIdx + 1) % placeholders.length;
            textarea.style.transition = 'opacity 0.3s ease';
            textarea.style.opacity = '0.5';
            setTimeout(() => {
                textarea.placeholder = placeholders[pIdx];
                textarea.style.opacity = '1';
            }, 300);
        }
    }, 8000);
}

/* ── Chatbot experience ── */
function initChatbot() {
    const form = document.getElementById('chat-form');
    const thread = document.getElementById('chat-thread');
    const input = document.getElementById('chat-input');
    const submit = document.getElementById('chat-submit');
    if (!form || !thread || !input || !submit) return;

    const label = document.getElementById('insight-label');
    const confidence = document.getElementById('insight-confidence');
    const model = document.getElementById('insight-model');
    const status = document.getElementById('insight-status');

    const appendMessage = (role, text, extra = {}) => {
        const article = document.createElement('article');
        article.className = `chat-message ${role === 'user' ? 'chat-message-user' : 'chat-message-bot'}`;

        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${role === 'user' ? 'message-avatar-user' : 'message-avatar-bot'}`;
        avatar.textContent = role === 'user' ? 'You' : 'K';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        const main = document.createElement('p');
        main.textContent = text;
        bubble.appendChild(main);

        if (Array.isArray(extra.suggestions) && extra.suggestions.length) {
            const list = document.createElement('ul');
            list.className = 'message-suggestions';
            extra.suggestions.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                list.appendChild(li);
            });
            bubble.appendChild(list);
        }

        if (extra.disclaimer) {
            const note = document.createElement('p');
            note.className = 'message-disclaimer';
            note.textContent = extra.disclaimer;
            bubble.appendChild(note);
        }

        article.appendChild(avatar);
        article.appendChild(bubble);
        thread.appendChild(article);
        thread.scrollTop = thread.scrollHeight;
    };

    document.querySelectorAll('[data-chat-starter]').forEach(button => {
        button.addEventListener('click', () => {
            input.value = button.dataset.chatStarter || '';
            input.focus();
            input.dispatchEvent(new Event('input', { bubbles: true }));
        });
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (text.length < 10) return;

        appendMessage('user', text);
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        submit.disabled = true;
        submit.textContent = 'Thinking...';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ text })
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Unable to respond right now.');
            }

            appendMessage('bot', data.reply, {
                suggestions: data.suggestions,
                disclaimer: data.disclaimer
            });

            label.textContent = data.analysis.label;
            confidence.textContent = `${data.analysis.confidence}%`;
            model.textContent = data.analysis.model;
            status.textContent = data.analysis.status;
        } catch (error) {
            appendMessage('bot', error.message);
        } finally {
            submit.disabled = false;
            submit.textContent = 'Send message';
        }
    });
}

/* ── Google Auth (simplified for demo) ── */
function initGoogleAuth() {
    const triggers = document.querySelectorAll('.js-google-auth');
    if (!triggers.length) return;

    const signInWithGoogle = function() {
        const email = prompt('Enter your Google email address:');
        if (!email) return;

        if (!email.includes('@')) {
            alert('Please enter a valid email address.');
            return;
        }

        fetch('/auth/google', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                email: email,
                name: email.split('@')[0].replace(/[._]/g, ' '),
                google_id: 'google_' + Date.now(),
                picture: null
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect;
            } else {
                alert(data.error || 'Authentication failed. Please try again.');
            }
        })
        .catch(() => {
            alert('Connection error. Please try again.');
        });
    };

    triggers.forEach(trigger => {
        trigger.addEventListener('click', signInWithGoogle);
    });
}

/* ── Breathing Exercise Widget ── */
function initBreathingWidget() {
    const resultCard = document.querySelector('.result-depressive');
    if (!resultCard) return;

    // Only show for depressive results
    const card = resultCard.closest('.result-card') || resultCard.closest('.card');
    if (!card) return;

    const breatheWidget = document.createElement('div');
    breatheWidget.className = 'breathe-widget';
    breatheWidget.innerHTML = `
        <div style="
            margin-top: 2rem;
            padding: 1.75rem;
            background: linear-gradient(135deg, rgba(181, 201, 183, 0.15), rgba(168, 197, 218, 0.12));
            border-radius: 20px;
            border: 1px solid rgba(181, 201, 183, 0.25);
            text-align: center;
        ">
            <p style="font-family: 'Playfair Display', serif; font-size: 1.1rem; color: #3D2C2E; margin-bottom: 1rem;">
                Take a moment to breathe
            </p>
            <div id="breathe-circle" style="
                width: 80px; height: 80px;
                border-radius: 50%;
                background: linear-gradient(135deg, rgba(181, 201, 183, 0.4), rgba(168, 197, 218, 0.3));
                margin: 0 auto 1rem;
                display: flex; align-items: center; justify-content: center;
                font-size: 0.85rem; color: #6B5B5E;
                border: 2px solid rgba(181, 201, 183, 0.3);
                transition: all 4s ease-in-out;
            ">
                <span id="breathe-text">Breathe in</span>
            </div>
            <p style="font-size: 0.82rem; color: #8E7D80;">
                Follow the circle — inhale as it grows, exhale as it shrinks
            </p>
            <button type="button" class="btn btn-outline js-breathing-toggle" style="margin-top: 1rem; padding: 0.5rem 1.2rem; font-size: 0.85rem;">
                Start breathing exercise
            </button>
        </div>
    `;

    card.appendChild(breatheWidget);
    const button = breatheWidget.querySelector('.js-breathing-toggle');
    if (button) {
        button.addEventListener('click', () => toggleBreathing(button));
    }
}

let breatheInterval = null;

function toggleBreathing(btn) {
    const circle = document.getElementById('breathe-circle');
    const text = document.getElementById('breathe-text');

    if (breatheInterval) {
        clearInterval(breatheInterval);
        breatheInterval = null;
        btn.textContent = 'Start breathing exercise';
        circle.style.transform = 'scale(1)';
        text.textContent = 'Breathe in';
        return;
    }

    btn.textContent = 'Stop';
    let phase = 'in';

    function cycle() {
        if (phase === 'in') {
            circle.style.transform = 'scale(1.4)';
            circle.style.background = 'linear-gradient(135deg, rgba(168, 197, 218, 0.5), rgba(181, 201, 183, 0.4))';
            text.textContent = 'Breathe in...';
            phase = 'hold';
        } else if (phase === 'hold') {
            text.textContent = 'Hold...';
            phase = 'out';
        } else {
            circle.style.transform = 'scale(1)';
            circle.style.background = 'linear-gradient(135deg, rgba(181, 201, 183, 0.4), rgba(168, 197, 218, 0.3))';
            text.textContent = 'Breathe out...';
            phase = 'in';
        }
    }

    cycle();
    breatheInterval = setInterval(cycle, 4000);
}

/* ── Gentle Tooltips ── */
function initGentleTooltips() {
    // Add supportive tooltips to key elements
    const submitBtn = document.querySelector('#chat-submit') || document.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.title = 'Your text is processed privately and securely';
    }

    // Gentle hover effect on history items
    document.querySelectorAll('.history-item').forEach(item => {
        item.classList.add('fade-in-item');
    });
}

/* ── Warm time-based greeting ── */
function getWarmGreeting(name) {
    const hour = new Date().getHours();
    if (hour < 12) return `Good morning, ${name}`;
    if (hour < 17) return `Good afternoon, ${name}`;
    if (hour < 21) return `Good evening, ${name}`;
    return `Hello, ${name}`;
}

function initWarmGreeting() {
    const welcomeH1 = document.querySelector('.welcome h1');
    if (!welcomeH1) return;

    const nameMatch = welcomeH1.textContent.match(/Welcome,\s*(.+)!/);
    if (nameMatch) {
        welcomeH1.textContent = getWarmGreeting(nameMatch[1]);
    }
}
