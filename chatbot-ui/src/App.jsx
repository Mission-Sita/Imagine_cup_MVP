import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Bot, User } from 'lucide-react';
import './App.css';

const App = () => {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null); // Reference for the input box

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Auto-resize logic
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'; // Reset height to recalculate
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`; // Set to scroll height
    }
  }, [prompt]);

  const handleSend = async () => {
    if (!prompt.trim()) return;

    const userMessage = { text: prompt, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setPrompt('');
    setIsLoading(true);
    
    // Reset height manually after sending
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.text,
          thread_id: "user_session_01"
        }),
      });

      const data = await response.json();
      const botMessage = { text: data.response, sender: 'bot' };
      setMessages((prev) => [...prev, botMessage]);

    } catch (error) {
      console.error("Error:", error);
      const errorMessage = { text: "Error connecting to server.", sender: 'bot' };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // Prevent default new line
      handleSend();
    }
  };

  return (
    <div className="main-container">
      <div className="content-wrapper">
        
        {messages.length === 0 ? (
          <div className="greeting-section">
            <h1 className="greeting-text">Hello, AKN.</h1>
            <p className="sub-text">How can I help you today?</p>
          </div>
        ) : (
          <div className="chat-container">
            {messages.map((msg, index) => (
              <div key={index} className={`message-row ${msg.sender === 'user' ? 'user-row' : 'bot-row'}`}>
                {msg.sender === 'bot' && <div className="avatar bot-avatar"><Bot size={18} /></div>}
                <div className={`message-bubble ${msg.sender === 'user' ? 'user-bubble' : 'bot-bubble'}`}>
                  {msg.text}
                </div>
                {msg.sender === 'user' && <div className="avatar user-avatar"><User size={18} /></div>}
              </div>
            ))}
            
            {isLoading && (
              <div className="message-row bot-row">
                <div className="avatar bot-avatar"><Bot size={18} /></div>
                <div className="message-bubble bot-bubble thinking-bubble">
                  <span className="dot"></span><span className="dot"></span><span className="dot"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* --- UPDATED INPUT AREA --- */}
        <div className="input-area">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              placeholder="Enter a prompt here"
              className="prompt-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              rows={1} // Start with 1 row
            />
            <button className="send-btn" onClick={handleSend} disabled={isLoading}>
              <Send size={20} color="white" />
            </button>
          </div>
          
          <p className="disclaimer-text">
            I can help you assist with cybersecurity related task and ready for a chat too.
          </p>
        </div>

        <div className="corner-icon">
          <Sparkles size={24} color="#a1a1aa" />
        </div>

      </div>
    </div>
  );
};

export default App;