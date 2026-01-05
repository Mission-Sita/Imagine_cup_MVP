const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class AuthService {
  async startPTTAgent(sessionId, goal, target, constraints = {}) {
    try {
      const response = await fetch(`${API_URL}/api/agent/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          goal,
          target,
          constraints
        })
      });

      if (!response.ok) {
        throw new Error('Failed to start PTT agent');
      }

      return await response.json();
    } catch (error) {
      console.error('Start PTT agent error:', error);
      throw error;
    }
  }

  streamPTTAgent(sessionId, onMessage, onError, onComplete) {
    const eventSource = new EventSource(`${API_URL}/api/agent/stream/${sessionId}`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
        
        if (data.type === 'complete') {
          eventSource.close();
          if (onComplete) onComplete();
        }
      } catch (error) {
        console.error('Parse error:', error);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      eventSource.close();
      if (onError) onError(error);
    };
    
    return eventSource;
  }

  async sendPTTInput(sessionId, data) {
    try {
      const response = await fetch(`${API_URL}/api/agent/input`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          data
        })
      });

      if (!response.ok) {
        throw new Error('Failed to send input');
      }

      return await response.json();
    } catch (error) {
      console.error('Send PTT input error:', error);
      throw error;
    }
  }

  async stopPTTAgent(sessionId) {
    try {
      const response = await fetch(`${API_URL}/api/agent/stop/${sessionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to stop agent');
      }

      return await response.json();
    } catch (error) {
      console.error('Stop PTT agent error:', error);
      throw error;
    }
  }
}

export default new AuthService();
