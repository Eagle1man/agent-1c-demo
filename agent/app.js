// АгентМост 2.0 — компонент интерфейса

class AgentInterface {
    constructor() {
        this.agents = [
            { id: 'coordinator', name: 'Координатор', avatar: '🎯', status: 'idle' },
            { id: 'warehouse', name: 'Кладовщик', avatar: '📦', status: 'idle' },
            { id: 'accountant', name: 'Бухгалтер', avatar: '📊', status: 'idle' },
            { id: 'logistics', name: 'Логист', avatar: '🚚', status: 'idle' },
            { id: 'procurement', name: 'Закупки', avatar: '📥', status: 'idle' },
            { id: 'sales', name: 'Продажи', avatar: '💰', status: 'idle' },
            { id: 'audit', name: 'Аудит', avatar: '🔍', status: 'idle' },
        ];
        this.tasks = [];
        this.chatMessages = [];
        this.currentAgent = 'coordinator';
        this.isMock = true;

        this.init();
    }

    init() {
        this.bindEvents();
        this.renderAgents();
        this.renderTasks();
        this.updateStats();
        this.startPolling();
        this.showConnectedState();
    }

    bindEvents() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const refreshBtn = document.getElementById('refresh-btn');
        const toggleMode = document.getElementById('toggle-mode');
        const modeLabel = document.getElementById('mode-label');

        sendBtn.addEventListener('click', () => this.sendMessage());
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        refreshBtn.addEventListener('click', () => this.refreshData());

        toggleMode.addEventListener('click', () => {
            this.isMock = !this.isMock;
            modeLabel.textContent = this.isMock ? '🔧 Режим эмуляции' : '🌐 Режим 1С';
            this.updateModeStatus();
        });
    }

    showConnectedState() {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('app').classList.remove('hidden');
        document.getElementById('exchange-path').textContent = 'C:\\1c_agent\\exchange';
        this.updateStatusUI();
    }    renderAgents() {
        const grid = document.getElementById('agents-grid');
        grid.innerHTML = this.agents.map(agent => `
            <div class="agent-card" data-agent="${agent.id}">
                <div class="agent-avatar" style="background: ${agent.color}20;">
                    ${agent.avatar}
                </div>
                <h3>${agent.name}</h3>
                <div class="agent-status">
                    <span class="status-dot-small idle"></span>
                    <span id="status-${agent.id}">Ожидание</span>
                </div>
            </div>
        `).join('');

        grid.querySelectorAll('.agent-card').forEach(card => {
            card.addEventListener('click', () => this.setActiveAgent(card.dataset.agent));
        });
    }

    setActiveAgent(agentId) {
        this.currentAgent = agentId;
        document.querySelectorAll('.agent-card').forEach(card => {
            card.classList.toggle('active', card.dataset.agent === agentId);
        });
        this.updateAgentStatus();
        this.addChatMessage('bot', `Текущий агент: ${this.agents.find(a => a.id === agentId).name}`);
    }

    updateAgentStatus() {
        const activeAgent = document.querySelector('.agent-card.active');
        if (activeAgent) {
            const agentId = activeAgent.dataset.agent;
            const statusEl = document.getElementById(`status-${agentId}`);
            if (statusEl) statusEl.textContent = 'Активен';
            activeAgent.classList.add('active');
        }
    }

    renderTasks() {
        const list = document.getElementById('tasks-list');
        const taskCount = document.getElementById('task-count');
        const statsTask = document.getElementById('stat-tasks');

        if (this.tasks.length === 0) {
            list.innerHTML = '<div class="chat-empty" style="min-height:100px; text-align:center;">Задач пока нет</div>';
            taskCount.textContent = '0 задач';
            statsTask.textContent = '0';
            return;
        }

        list.innerHTML = this.tasks.slice(-5).reverse().map(task => `
            <div class="task-item">
                <div class="task-icon">${task.icon || '📋'}</div>
                <div class="task-content">
                    <div class="task-subject">${task.subject}</div>
                    <div class="task-detail">${task.detail}</div>
                    <div class="task-meta">
                        <span>🕐 ${task.time}</span>
                        <span class="status-dot-small ${task.status === 'done' ? 'running' : 'idle'}"></span>
                    </div>
                </div>
            </div>
        `).join('');

        taskCount.textContent = `${this.tasks.length} задач`;
        statsTask.textContent = this.tasks.length;
    }    addChatMessage(sender, content, type = 'text', detail = null) {
        this.chatMessages.push({ sender, content, type, time: new Date().toLocaleTimeString('ru-RU') });

        const messagesEl = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;

        let contentHtml = `
            <div class="msg-avatar">${sender === 'user' ? '👤' : '🤖'}</div>
            <div class="msg-content">
        `;

        if (type === 'text') {
            contentHtml += `<p>${this.escapeHtml(content)}</p>`;
        } else if (type === 'pending') {
            contentHtml += `
                <div class="msg-block">
                    <h4>⏳ Ожидание подтверждения</h4>
                    <p>Агент требует вашего решения перед выполнением действия.</p>
                </div>
                <div class="msg-block">
                    <h4>Что делать?</h4>
                    <div class="btn-group">
                        <button class="btn-ok" onclick="app.confirmAction('${sender}', 'yes')">✅ Да, выполнить</button>
                        <button class="btn-cancel" onclick="app.confirmAction('${sender}', 'no')">❌ Нет, отмена</button>
                    </div>
                </div>
            `;
        } else if (type === 'result') {
            contentHtml += `
                <div class="msg-block">
                    <h4>${detail?.title || 'Результат'}</h4>
                    <p>${this.escapeHtml(detail?.text || content)}</p>
                </div>
            `;
        }

        contentHtml += '</div>';
        messageDiv.innerHTML = contentHtml;
        messagesEl.appendChild(messageDiv);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    addTask(task) {
        this.tasks.push(task);
        this.renderTasks();
    }

    updateStats() {
        document.getElementById('stat-agents').textContent = this.agents.length;
        document.getElementById('stat-tasks').textContent = this.tasks.length;
    }

    updateStatusUI() {
        document.getElementById('agent-count').textContent = `${this.agents.length} агентов`;
        document.getElementById('mode-status').textContent = this.isMock ? 'Режим: эмулятор' : 'Режим: 1С';
    }

    startPolling() {
        setInterval(() => {
            this.refreshData();
        }, 5000);
    }

    refreshData() {
        this.updateStatusUI();
        this.updateAgentStatus();
    }    sendMessage() {
        const input = document.getElementById('chat-input');
        const text = input.value.trim();
        if (!text) return;

        this.addChatMessage('user', text);
        input.value = '';
        this.addChatMessage('bot', '⏳ Обрабатывается...', 'pending');
        document.getElementById('send-btn').disabled = true;

        setTimeout(() => {
            this.respondToMessage(text);
            document.getElementById('send-btn').disabled = false;
        }, 1500 + Math.random() * 1000);
    }

    respondToMessage(text) {
        const lower = text.toLowerCase();

        if (lower.includes('связ') || lower.includes('проверь') || lower.includes('проверка')) {
            this.addChatMessage('bot', '✅ Связь с 1С установлена.', 'result', {
                title: 'Проверка связи',
                text: 'Система подключена. Все агенты готовы к работе.'
            });
        } else if (lower.includes('остаток') || lower.includes('склад') || lower.includes('товар')) {
            this.addChatMessage('bot', '📦 Запрос к 1С: остатки на складе', 'result', {
                title: 'Остатки на складе',
                text: 'Кладовщик сверяет остатки. Товаров на складе: 1577 шт.'
            });
        } else if (lower.includes('задолжен') || lower.includes('контрагент') || lower.includes('долг')) {
            this.addChatMessage('bot', '📊 Запрос к 1С: задолженность', 'result', {
                title: 'Задолженность контрагентов',
                text: 'Бухгалтер проверяет остатки по счетам.'
            });
        } else if (lower.includes('налк') || lower.includes('созд') || lower.includes('документ')) {
            this.addChatMessage('bot', '📝 Создание документа', 'pending');
        } else {
            this.addChatMessage('bot', '🤖 Я понимаю запросы к 1С. Спросите о: остатках, задолженности, проведении документов, отгрузках.');
        }
    }

    confirmAction(agent, action) {
        this.addChatMessage('bot', `Вы выбрали: ${action === 'yes' ? '✅ выполнить' : '❌ отменить'}`);

        const agentName = this.agents.find(a => a.id === agent)?.name || 'агент';
        this.addChatMessage('bot', `Действие выполнено для ${agentName}.`, 'result', {
            title: 'Подтверждение',
            text: `Действие ${action} для ${agentName}.`
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new AgentInterface();
});

function updateStats() {
    if (window.app) {
        window.app.updateStats();
    }
}
