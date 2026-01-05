import React, { useState, useEffect, useRef } from 'react';
import { Shield, Play, Square, Send, AlertCircle, CheckCircle, Clock, Terminal, Zap, Target, List } from 'lucide-react';
import authService from '../services/authService';

export default function PTTInterface() {
  const [sessionId, setSessionId] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [goal, setGoal] = useState('');
  const [target, setTarget] = useState('');
  const [scope, setScope] = useState('external');
  
  const [logs, setLogs] = useState([]);
  const [currentTask, setCurrentTask] = useState(null);
  const [taskTree, setTaskTree] = useState([]);
  const [userInputRequired, setUserInputRequired] = useState(false);
  const [userInputPrompt, setUserInputPrompt] = useState('');
  const [userInputValue, setUserInputValue] = useState('');
  const [stats, setStats] = useState({ total: 0, completed: 0, pending: 0, failed: 0 });
  
  const logsEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  const startPTTAgent = async () => {
    if (!goal.trim() || !target.trim()) {
      alert('Please enter both goal and target!');
      return;
    }

    const newSessionId = `session_${Date.now()}`;
    setSessionId(newSessionId);
    setLogs([]);
    setTaskTree([]);
    setIsRunning(true);

    try {
      // Start agent
      await authService.startPTTAgent(newSessionId, goal, target, { scope });

      addLog('info', `🚀 PTT Agent started for target: ${target}`);
      addLog('info', `🎯 Goal: ${goal}`);

      // Start streaming
      const eventSource = authService.streamPTTAgent(
        newSessionId,
        handleAgentMessage,
        handleAgentError,
        handleAgentComplete
      );
      
      eventSourceRef.current = eventSource;

    } catch (error) {
      addLog('error', `❌ Failed to start agent: ${error.message}`);
      setIsRunning(false);
    }
  };

  const stopPTTAgent = async () => {
    if (!sessionId) return;

    try {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      await authService.stopPTTAgent(sessionId);
      addLog('info', '🛑 Agent stopped by user');
      setIsRunning(false);
      setSessionId(null);
    } catch (error) {
      addLog('error', `Failed to stop agent: ${error.message}`);
    }
  };

  const handleAgentMessage = (data) => {
    const { type, payload } = data;

    switch (type) {
      case 'status':
        addLog('status', payload);
        break;

      case 'info':
        addLog('info', payload);
        break;

      case 'log':
        addLog('log', payload);
        setCurrentTask(payload);
        break;

      case 'tool_use':
        addLog(
          'thinking',
          `🔧 Tool: ${payload.name} ${JSON.stringify(payload.args)}`
        );
        break;

      case 'summary':
        addLog('success', payload);
        break;

      case 'success':
        addLog('success', payload);
        break;

      case 'tree_state':
        setTaskTree(payload);
        addLog('info', '🌳 Task tree updated');
        break;

      case 'question':
        setUserInputRequired(true);
        setUserInputPrompt(payload);
        addLog('input', `❓ ${payload}`);
        break;

      case 'error':
        addLog('error', payload);
        break;

      default:
        // IMPORTANT: prevents silent drops in future
        addLog('info', `[${type}] ${JSON.stringify(payload)}`);
    }
  };


  const handleAgentError = () => {
    addLog('status', '🔌 Agent connection closed');
    setIsRunning(false);
  };

  const handleAgentComplete = () => {
    addLog('status', '✅ Agent finished execution');
    setIsRunning(false);
  };

  const sendUserInput = async () => {
    if (!userInputValue.trim() || !sessionId) return;

    try {
      await authService.sendPTTInput(sessionId, userInputValue);
      addLog('user_input', `👤 User: ${userInputValue}`);
      setUserInputValue('');
      setUserInputRequired(false);
      setUserInputPrompt('');
    } catch (error) {
      addLog('error', `Failed to send input: ${error.message}`);
    }
  };

  const addLog = (type, message) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { type, message, timestamp }]);

    // Update stats
    if (message.includes('completed') || message.includes('✅')) {
      setStats(prev => ({ ...prev, completed: prev.completed + 1 }));
    }
  };

  const getLogIcon = (type) => {
    switch (type) {
      case 'status':
        return <Clock className="w-4 h-4 text-blue-400" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'thinking':
        return <Zap className="w-4 h-4 text-yellow-400" />;
      case 'input':
        return <Terminal className="w-4 h-4 text-purple-400" />;
      default:
        return <Terminal className="w-4 h-4 text-gray-400" />;
    }
  };

  const getLogColor = (type) => {
    switch (type) {
      case 'status':
        return 'text-blue-300';
      case 'success':
        return 'text-green-300';
      case 'error':
        return 'text-red-300';
      case 'thinking':
        return 'text-yellow-300';
      case 'input':
        return 'text-purple-300';
      case 'user_input':
        return 'text-cyan-300';
      default:
        return 'text-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center justify-between bg-black bg-opacity-50 backdrop-blur-lg border border-cyan-500 border-opacity-30 rounded-2xl p-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-2xl flex items-center justify-center">
              <Shield className="w-9 h-9 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                PTT Agent
              </h1>
              <p className="text-sm text-gray-400">Autonomous Penetration Testing</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs text-gray-400">Status</p>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`} />
                <p className="text-sm font-semibold">{isRunning ? 'Running' : 'Idle'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-4 gap-6">
        {/* Left Panel - Configuration */}
        <div className="col-span-1">
          <div className="bg-black bg-opacity-50 backdrop-blur-lg border border-cyan-500 border-opacity-30 rounded-2xl p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-cyan-400" />
              Configuration
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Goal</label>
                <input
                  type="text"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="e.g., Enumerate attack surface"
                  disabled={isRunning}
                  className="w-full bg-gray-800 border border-cyan-500 border-opacity-30 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Target</label>
                <input
                  type="text"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  placeholder="e.g., example.com"
                  disabled={isRunning}
                  className="w-full bg-gray-800 border border-cyan-500 border-opacity-30 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Scope</label>
                <select
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  disabled={isRunning}
                  className="w-full bg-gray-800 border border-cyan-500 border-opacity-30 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
                >
                  <option value="external">External</option>
                  <option value="internal">Internal</option>
                  <option value="full">Full</option>
                </select>
              </div>

              {!isRunning ? (
                <button
                  onClick={startPTTAgent}
                  className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white rounded-lg px-6 py-3 flex items-center justify-center gap-2 transition-all shadow-lg"
                >
                  <Play className="w-5 h-5" />
                  Start PTT Agent
                </button>
              ) : (
                <button
                  onClick={stopPTTAgent}
                  className="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white rounded-lg px-6 py-3 flex items-center justify-center gap-2 transition-all shadow-lg"
                >
                  <Square className="w-5 h-5" />
                  Stop Agent
                </button>
              )}
            </div>

            {/* Stats */}
            <div className="mt-6 grid grid-cols-2 gap-3">
              <div className="bg-gray-800 bg-opacity-50 rounded-lg p-3">
                <p className="text-xs text-gray-400">Completed</p>
                <p className="text-2xl font-bold text-green-400">{stats.completed}</p>
              </div>
              <div className="bg-gray-800 bg-opacity-50 rounded-lg p-3">
                <p className="text-xs text-gray-400">Total Logs</p>
                <p className="text-2xl font-bold text-cyan-400">{logs.length}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Logs & Output */}
        <div className="col-span-3 space-y-4">
          {/* Current Task */}
          {currentTask && isRunning && (
            <div className="bg-gradient-to-r from-blue-900 to-purple-900 bg-opacity-50 backdrop-blur-lg border border-blue-500 border-opacity-50 rounded-2xl p-4">
              <div className="flex items-center gap-3">
                <div className="animate-spin">
                  <Zap className="w-6 h-6 text-yellow-400" />
                </div>
                <div>
                  <p className="text-xs text-gray-300 font-semibold">Current Task</p>
                  <p className="text-sm text-white">{currentTask}</p>
                </div>
              </div>
            </div>
          )}

          {/* User Input Required */}
          {userInputRequired && (
            <div className="bg-gradient-to-r from-purple-900 to-pink-900 bg-opacity-50 backdrop-blur-lg border border-purple-500 border-opacity-50 rounded-2xl p-4">
              <p className="text-sm text-gray-200 mb-3">❓ {userInputPrompt}</p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={userInputValue}
                  onChange={(e) => setUserInputValue(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendUserInput()}
                  placeholder="Enter your response..."
                  className="flex-1 bg-gray-800 border border-purple-500 border-opacity-30 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <button
                  onClick={sendUserInput}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-lg px-6 py-2 flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  Send
                </button>
              </div>
            </div>
          )}

          {/* Logs Terminal */}
          <div className="bg-black bg-opacity-70 backdrop-blur-lg border border-cyan-500 border-opacity-30 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-cyan-400 flex items-center gap-2">
                <Terminal className="w-4 h-4" />
                Agent Logs
              </h3>
              <button
                onClick={() => setLogs([])}
                className="text-xs text-gray-400 hover:text-white transition-colors"
              >
                Clear
              </button>
            </div>

            <div className="h-[600px] overflow-y-auto space-y-2 font-mono text-xs">
              {logs.length === 0 ? (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <p>No logs yet. Start the agent to see activity.</p>
                </div>
              ) : (
                logs.map((log, idx) => (
                  <div key={idx} className="flex items-start gap-2 hover:bg-gray-800 hover:bg-opacity-30 p-2 rounded">
                    {getLogIcon(log.type)}
                    <span className="text-gray-500 text-xs">{log.timestamp}</span>
                    <span className={`flex-1 ${getLogColor(log.type)}`}>{log.message}</span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}