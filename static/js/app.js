/**
 * FakeLM Chat UI - Main application controller.
 */

(function () {
  'use strict';

  // --- State ---
  const chatManager = new ChatManager();
  let currentModel = 'fake-gpt-4';
  let isGenerating = false;
  let streamController = null;
  let accumulatedContent = '';

  // --- DOM References ---
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    sidebar: $('#sidebar'),
    chatList: $('#chat-list'),
    newChatBtn: $('#new-chat-btn'),
    toggleSidebar: $('#toggle-sidebar'),
    modelSelector: $('#model-selector'),
    statusDot: $('#status-dot'),
    statusText: $('#status-text'),
    messagesArea: $('#messages-area'),
    userInput: $('#user-input'),
    sendBtn: $('#send-btn'),
    // Settings
    temperatureSlider: $('#temperature'),
    temperatureVal: $('#temperature-val'),
    maxTokensInput: $('#max-tokens'),
    intelligenceSlider: $('#intelligence'),
    intelligenceVal: $('#intelligence-val'),
    seedInput: $('#seed'),
  };

  // --- Initialization ---
  async function init() {
    renderChatList();
    renderMessages();
    bindEvents();
    await loadModels();
  }

  async function loadModels() {
    try {
      const models = await FakeLMAPI.getModels();
      dom.modelSelector.innerHTML = '';
      models.forEach((m) => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.id;
        dom.modelSelector.appendChild(opt);
      });
      if (models.length > 0) {
        currentModel = models[0].id;
        dom.modelSelector.value = currentModel;
      }
    } catch (err) {
      showToast('Failed to load models: ' + err.message, 'error');
    }
  }

  // --- Event Binding ---
  function bindEvents() {
    // New chat
    dom.newChatBtn.addEventListener('click', () => {
      chatManager.newChat();
      renderChatList();
      renderMessages();
      dom.userInput.focus();
    });

    // Toggle sidebar
    dom.toggleSidebar.addEventListener('click', () => {
      dom.sidebar.classList.toggle('collapsed');
    });

    // Model change
    dom.modelSelector.addEventListener('change', () => {
      currentModel = dom.modelSelector.value;
    });

    // Send button
    dom.sendBtn.addEventListener('click', handleSend);

    // Enter to send, Shift+Enter for newline
    dom.userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });

    // Auto-resize textarea
    dom.userInput.addEventListener('input', () => {
      dom.userInput.style.height = 'auto';
      dom.userInput.style.height = Math.min(dom.userInput.scrollHeight, 200) + 'px';
    });

    // Settings - update displayed values
    dom.temperatureSlider.addEventListener('input', () => {
      dom.temperatureVal.textContent = parseFloat(dom.temperatureSlider.value).toFixed(2);
    });
    dom.intelligenceSlider.addEventListener('input', () => {
      dom.intelligenceVal.textContent = parseFloat(dom.intelligenceSlider.value).toFixed(2);
    });
  }

  // --- Chat List Delegation ---
  dom.chatList.addEventListener('click', (e) => {
    const item = e.target.closest('.chat-item');
    if (!item) return;

    const id = item.dataset.id;

    // Delete button clicked
    if (e.target.closest('.chat-item-delete')) {
      e.stopPropagation();
      chatManager.deleteChat(id);
      renderChatList();
      renderMessages();
      return;
    }

    // Switch chat
    chatManager.switchChat(id);
    renderChatList();
    renderMessages();
  });

  // --- Suggestion chips ---
  dom.messagesArea.addEventListener('click', (e) => {
    const chip = e.target.closest('.suggestion-chip');
    if (!chip) return;
    dom.userInput.value = chip.textContent;
    handleSend();
  });

  // --- Send Handler ---
  async function handleSend() {
    if (isGenerating) {
      // Stop generation
      stopGeneration();
      return;
    }

    const text = dom.userInput.value.trim();
    if (!text) return;

    // Disable input
    dom.userInput.value = '';
    dom.userInput.style.height = 'auto';
    setGenerating(true);

    // Add user message
    chatManager.addMessage('user', text);
    renderMessages();

    // Prepare API messages
    const messages = chatManager.getMessagesForAPI();

    const params = {
      model: currentModel,
      messages,
      max_tokens: parseInt(dom.maxTokensInput.value, 10) || 100,
      temperature: parseFloat(dom.temperatureSlider.value),
      intelligence: parseFloat(dom.intelligenceSlider.value),
      seed: dom.seedInput.value,
    };

    accumulatedContent = '';

    const onStats = (stats) => {
      chatManager.updateLastAssistantStats(stats);
      renderMessages(false);
    };

    streamController = FakeLMAPI.streamChatCompletion(
      params,
      // onToken
      (token, isFirst) => {
        accumulatedContent += token;
        chatManager.updateLastAssistantMessage(accumulatedContent);
        renderMessages(true);
      },
      // onDone
      (reason) => {
        setGenerating(false);
        streamController = null;
        renderMessages(false);
        renderChatList();
        if (reason === 'aborted') {
          showToast('Generation stopped.', 'info');
        }
      },
      // onError
      (err) => {
        setGenerating(false);
        streamController = null;
        const errorMsg = `Error: ${err.message}`;
        chatManager.addMessage('assistant', errorMsg);
        renderMessages(false);
        renderChatList();
        showToast(err.message, 'error');
      },
      // onStats
      onStats
    );
  }

  function stopGeneration() {
    if (streamController) {
      streamController.abort();
      streamController = null;
    }
  }

  function setGenerating(gen) {
    isGenerating = gen;
    if (gen) {
      dom.sendBtn.innerHTML = '⏹';
      dom.sendBtn.classList.add('stop-btn');
      dom.sendBtn.title = 'Stop generation';
      dom.userInput.disabled = true;
      dom.statusDot.classList.add('generating');
      dom.statusText.textContent = 'Generating...';
    } else {
      dom.sendBtn.innerHTML = '➤';
      dom.sendBtn.classList.remove('stop-btn');
      dom.sendBtn.title = 'Send message';
      dom.userInput.disabled = false;
      dom.statusDot.classList.remove('generating');
      dom.statusText.textContent = 'Ready';
      dom.userInput.focus();
    }
  }

  // --- Rendering ---
  function renderChatList() {
    const chats = chatManager.chats;
    const activeId = chatManager.activeChat?.id;

    dom.chatList.innerHTML = chats
      .map(
        (c) => `
      <div class="chat-item${c.id === activeId ? ' active' : ''}" data-id="${c.id}">
        <span class="chat-item-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title)}</span>
        <button class="chat-item-delete" title="Delete chat">✕</button>
      </div>
    `
      )
      .join('');
  }

  function renderMessages(isStreaming = false) {
    const chat = chatManager.activeChat;

    if (!chat || chat.messages.length === 0) {
      dom.messagesArea.innerHTML = `
        <div class="empty-state">
          <h2>FakeLM</h2>
          <p>A simulated LLM API — type a message to see the generator in action.</p>
          <div class="suggestions">
            <span class="suggestion-chip">Hello! Who are you?</span>
            <span class="suggestion-chip">Tell me a short story</span>
            <span class="suggestion-chip">Explain quantum computing</span>
            <span class="suggestion-chip">Write a poem about coding</span>
          </div>
        </div>
      `;
      return;
    }

    let html = '';
    chat.messages.forEach((msg, index) => {
      const isLast = index === chat.messages.length - 1;
      const isAssistant = msg.role === 'assistant';
      const isCurrentlyStreaming = isLast && isAssistant && isStreaming;
      const roleLabel = isAssistant ? 'FakeLM' : 'You';
      const avatarIcon = isAssistant ? '🤖' : '👤';

      let contentHtml;
      if (isAssistant) {
        // Simple markdown-like rendering
        contentHtml = renderContent(msg.content);
      } else {
        contentHtml = escapeHtml(msg.content);
      }

      const cursorClass = isCurrentlyStreaming ? ' cursor-blink' : '';

      // Render stats footer if available
      let statsHtml = '';
      if (isAssistant && msg.stats) {
        const s = msg.stats;
        const engineLabel = s.engine || 'unknown';
        const elapsed = typeof s.elapsed === 'number' ? s.elapsed.toFixed(3) + 's' : '-';
        const tokens = s.tokens != null ? s.tokens : '-';
        const speed = typeof s.speed === 'number' ? Math.round(s.speed) : '-';
        statsHtml = `<div class="message-stats">Engine: ${escapeHtml(engineLabel)} &nbsp;|&nbsp; ${tokens} tokens &nbsp;|&nbsp; ${elapsed} &nbsp;|&nbsp; ${speed} tok/s</div>`;
      }

      html += `
        <div class="message ${isAssistant ? 'assistant-message' : 'user-message'}">
          <div class="message-avatar">${avatarIcon}</div>
          <div class="message-body">
            <div class="message-role">${roleLabel}</div>
            <div class="message-content${cursorClass}">
              ${contentHtml}
            </div>
            ${statsHtml}
          </div>
        </div>
      `;
    });

    dom.messagesArea.innerHTML = html;

    // Scroll to bottom
    dom.messagesArea.scrollTop = dom.messagesArea.scrollHeight;
  }

  function renderContent(text) {
    // Escape HTML
    let html = escapeHtml(text);

    // Code blocks ```
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre><code class="${lang}">${escapeHtml(code.trim())}</code></pre>`;
    });

    // Inline code `...`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold **...**
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic *...*
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // --- Toast ---
  function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 4000);
  }

  // --- Keyboard shortcut: Ctrl+K to toggle sidebar ---
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      dom.sidebar.classList.toggle('collapsed');
    }
  });

  // --- Start ---
  init();
})();