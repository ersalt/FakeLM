/**
 * FakeLM API Client - wraps all backend API calls.
 */

const API_BASE = '/v1';

const FakeLMAPI = {
  /**
   * Fetch available models from /v1/models.
   * @returns {Promise<Array<{id: string, owned_by: string}>>}
   */
  async getModels() {
    const resp = await fetch(`${API_BASE}/models`);
    if (!resp.ok) {
      throw new Error(`Failed to fetch models: ${resp.status}`);
    }
    const data = await resp.json();
    return data.data || [];
  },

  /**
   * Send a chat completion request (non-streaming).
   * @param {Object} params
   * @param {string} params.model
   * @param {Array<{role: string, content: string}>} params.messages
   * @param {number} [params.max_tokens]
   * @param {number} [params.temperature]
   * @param {number} [params.intelligence]
   * @param {number} [params.seed]
   * @returns {Promise<Object>} OpenAI-formatted response
   */
  async chatCompletion({ model, messages, max_tokens = 100, temperature = 1.0, intelligence = 0.5, seed = null }) {
    const body = {
      model,
      messages,
      max_tokens,
      temperature,
      intelligence,
      stream: false,
    };
    if (seed !== null && seed !== undefined && seed !== '') {
      body.seed = parseInt(seed, 10);
    }

    const resp = await fetch(`${API_BASE}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail?.[0]?.msg || errData.detail?.message || `HTTP ${resp.status}`);
    }

    return resp.json();
  },

  /**
   * Send a streaming chat completion request using SSE.
   * @param {Object} params
   * @param {function(string, boolean):void} onToken - called with (token, isFirst)
   * @param {function(Object):void} [onStats] - called with stats object when stream finishes
   * @param {function(string):void} onDone - called when stream finishes
   * @param {function(Error):void} onError - called on error
   * @returns {AbortController} controller to abort the request
   */
  streamChatCompletion({ model, messages, max_tokens = 100, temperature = 1.0, intelligence = 0.5, seed = null }, onToken, onDone, onError, onStats) {
    const body = {
      model,
      messages,
      max_tokens,
      temperature,
      intelligence,
      stream: true,
    };
    if (seed !== null && seed !== undefined && seed !== '') {
      body.seed = parseInt(seed, 10);
    }

    const controller = new AbortController();

    fetch(`${API_BASE}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail?.[0]?.msg || errData.detail?.message || `HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let isFirstToken = true;
        let lastEventType = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            // Handle named events
            if (trimmed.startsWith('event:')) {
              lastEventType = trimmed.slice(6).trim();
              continue;
            }

            if (!trimmed.startsWith('data:')) continue;

            const data = trimmed.slice(5).trim();
            if (data === '[DONE]') {
              onDone && onDone('stop');
              return;
            }

            // Handle x_fakellm_stats event
            if (lastEventType === 'x_fakellm_stats') {
              lastEventType = null;
              try {
                const stats = JSON.parse(data);
                onStats && onStats(stats);
              } catch (e) {
                // Skip malformed stats
              }
              continue;
            }

            lastEventType = null;

            try {
              const parsed = JSON.parse(data);
              const choices = parsed.choices || [];
              if (choices.length > 0) {
                const delta = choices[0].delta || {};
                const content = delta.content || '';
                if (content) {
                  onToken && onToken(content, isFirstToken);
                  isFirstToken = false;
                }
              }
            } catch (e) {
              // Skip malformed SSE lines
            }
          }
        }

        onDone && onDone('stop');
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError && onError(err);
        } else {
          onDone && onDone('aborted');
        }
      });

    return controller;
  },
};