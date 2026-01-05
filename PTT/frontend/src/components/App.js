import React, { useState } from 'react';
import PTTInterface from './PTTInterface';
import { Shield, Zap, Target, Lock } from 'lucide-react';

export default function App() {
  const [view, setView] = useState('home'); // 'home' or 'ptt'

  if (view === 'ptt') {
    return <PTTInterface onBack={() => setView('home')} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white">
      {/* Hero Section */}
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="text-center max-w-4xl">
          {/* Logo */}
          <div className="relative mb-8 inline-block">
            <div className="w-40 h-40 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-3xl flex items-center justify-center mx-auto transform rotate-3 shadow-2xl shadow-cyan-500/50 animate-pulse">
              <Shield className="w-24 h-24 text-white" />
            </div>
            <div className="absolute -top-4 -right-4 w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center shadow-xl animate-bounce">
              <Zap className="w-8 h-8 text-white" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-6xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent animate-pulse">
            PTT Agent
          </h1>

          <p className="text-xl md:text-2xl text-gray-300 mb-4">
            Autonomous Penetration Testing System
          </p>

          <p className="text-base text-gray-400 mb-12 max-w-2xl mx-auto">
            AI-powered security testing with intelligent task trees, real-time execution, and autonomous decision-making
          </p>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
            <div className="bg-black bg-opacity-40 backdrop-blur-lg border border-cyan-500 border-opacity-30 rounded-2xl p-6 hover:border-opacity-60 transition-all">
              <Target className="w-10 h-10 text-cyan-400 mb-3 mx-auto" />
              <h3 className="text-lg font-semibold mb-2">Smart Targeting</h3>
              <p className="text-sm text-gray-400">Intelligent task tree planning based on your security goals</p>
            </div>

            <div className="bg-black bg-opacity-40 backdrop-blur-lg border border-blue-500 border-opacity-30 rounded-2xl p-6 hover:border-opacity-60 transition-all">
              <Zap className="w-10 h-10 text-blue-400 mb-3 mx-auto" />
              <h3 className="text-lg font-semibold mb-2">Real-Time Execution</h3>
              <p className="text-sm text-gray-400">Live streaming of agent activities and tool outputs</p>
            </div>

            <div className="bg-black bg-opacity-40 backdrop-blur-lg border border-purple-500 border-opacity-30 rounded-2xl p-6 hover:border-opacity-60 transition-all">
              <Lock className="w-10 h-10 text-purple-400 mb-3 mx-auto" />
              <h3 className="text-lg font-semibold mb-2">MCP Integration</h3>
              <p className="text-sm text-gray-400">Connected to security tools via Model Context Protocol</p>
            </div>
          </div>

          {/* CTA Button */}
          <button
            onClick={() => setView('ptt')}
            className="group relative bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-lg font-bold px-12 py-5 rounded-2xl shadow-2xl shadow-cyan-500/40 transition-all transform hover:scale-105"
          >
            <span className="flex items-center gap-3">
              <Shield className="w-6 h-6" />
              Launch PTT Agent
              <Zap className="w-6 h-6 group-hover:animate-pulse" />
            </span>
          </button>

          <p className="text-xs text-gray-500 mt-4">
            Powered by LangChain, GPT-4, and MCP Servers
          </p>
        </div>
      </div>
    </div>
  );
}