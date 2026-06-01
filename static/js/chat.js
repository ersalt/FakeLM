/**
 * Chat Manager - handles conversation lifecycle and localStorage persistence.
 */

const STORAGE_KEY = 'fakellm_chats';
const ACTIVE_CHAT_KEY = 'fakellm_active_chat';

class ChatManager {
  constructor() {
    this._chats = this._load();
    this._activeId = localStorage.getItem(ACTIVE_CHAT_KEY) || null;
    // Ensure at least one chat exists
    if (this._chats.length === 0) {
      this.newChat();
    }
    // Validate active ID
    if (!this._chats.find(c => c.id === this._activeId)) {
      this._activeId = this._chats[0]?.id || null;
      this._saveActiveId();
    }
  }

  /**
   * Get all chats, sorted by last updated descending.
   */
  get chats() {
    return [...this._chats].sort((a, b) => b.updatedAt - a.updatedAt);
  }

  /**
   * Get the currently active chat.
   */
  get activeChat() {
    return this._chats.find(c => c.id === this._activeId) || null;
  }

  /**
   * Get or create the active chat (for sending messages).
   */
  getActiveChat() {
    let chat = this.activeChat;
    if (!chat) {
      chat = this.newChat();
    }
    return chat;
  }

  /**
   * Create a new empty chat.
   * @returns The newly created chat object.
   */
  newChat() {
    const chat = {
      id: this._generateId(),
      title: 'New Chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    this._chats.push(chat);
    this._activeId = chat.id;
    this._save();
    return chat;
  }

  /**
   * Switch the active chat.
   * @param {string} id
   */
  switchChat(id) {
    if (this._chats.find(c => c.id === id)) {
      this._activeId = id;
      this._saveActiveId();
    }
  }

  /**
   * Delete a chat by ID. If it's the active chat, switch to another.
   * @param {string} id
   */
  deleteChat(id) {
    const index = this._chats.findIndex(c => c.id === id);
    if (index === -1) return;

    this._chats.splice(index, 1);

    if (this._activeId === id) {
      this._activeId = this._chats.length > 0 ? this._chats[0].id : null;
    }

    // Always ensure at least one chat
    if (this._chats.length === 0) {
      this.newChat();
    }

    this._save();
  }

  /**
   * Add a message to the active chat.
   * @param {string} role - 'user' or 'assistant'
   * @param {string} content
   */
  addMessage(role, content) {
    const chat = this.getActiveChat();
    const msg = {
      id: this._generateId(),
      role,
      content,
      timestamp: Date.now(),
    };
    chat.messages.push(msg);
    chat.updatedAt = Date.now();

    // Auto-title: use first user message as title
    if (role === 'user' && chat.title === 'New Chat') {
      chat.title = content.slice(0, 50) + (content.length > 50 ? '...' : '');
    }

    this._save();
    return msg;
  }

  /**
   * Update the last assistant message (for streaming append).
   * @param {string} content - The full accumulated content so far
   */
  updateLastAssistantMessage(content) {
    const chat = this.getActiveChat();
    const lastMsg = chat.messages[chat.messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.content = content;
      lastMsg.timestamp = Date.now();
    } else {
      // No assistant message yet, create one
      chat.messages.push({
        id: this._generateId(),
        role: 'assistant',
        content,
        timestamp: Date.now(),
      });
    }
    chat.updatedAt = Date.now();
    this._save();
  }

  /**
   * Attach generation stats to the last assistant message.
   * @param {Object} stats - { engine, elapsed, tokens, speed }
   */
  updateLastAssistantStats(stats) {
    const chat = this.getActiveChat();
    const lastMsg = chat.messages[chat.messages.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.stats = stats;
      lastMsg.timestamp = Date.now();
    }
    chat.updatedAt = Date.now();
    this._save();
  }

  /**
   * Get messages for the active chat as OpenAI API format.
   */
  getMessagesForAPI() {
    const chat = this.activeChat;
    if (!chat) return [];
    return chat.messages.map(m => ({
      role: m.role,
      content: m.content,
    }));
  }

  // --- Persistence ---

  _load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  _save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this._chats));
    this._saveActiveId();
  }

  _saveActiveId() {
    if (this._activeId) {
      localStorage.setItem(ACTIVE_CHAT_KEY, this._activeId);
    } else {
      localStorage.removeItem(ACTIVE_CHAT_KEY);
    }
  }

  _generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }
}