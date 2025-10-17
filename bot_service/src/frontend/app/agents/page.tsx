'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { NextPage } from 'next';
import Link from 'next/link';
import { 
  User, 
  Plus, 
  RefreshCcw, 
  X, 
  XCircle,
  Search,
  Filter,
  Grid,
  List,
  Zap,
  Clock,
  Users,
  Activity,
  TrendingUp,
  Sparkles,
  Bot,
  UserCheck,
  Cpu
} from 'lucide-react';
import MainLayout from '../../components/layout/MainLayout';
import agentService, { Agent } from '../../services/agent';
import { toast } from 'react-hot-toast';
import { useTheme } from '../../contexts/ThemeContext';
import AgentCard from '../../components/agents/AgentCard';
import Button from '../../components/ui/Button';

// Enhanced animation styles with GPU acceleration
const animationStyles = `
  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translate3d(0, 20px, 0);
    }
    to {
      opacity: 1;
      transform: translate3d(0, 0, 0);
    }
  }
  .animate-fadeInUp {
    animation: fadeInUp 0.4s ease-out forwards;
  }

  @keyframes slideInRight {
    from {
      opacity: 0;
      transform: translate3d(30px, 0, 0);
    }
    to {
      opacity: 1;
      transform: translate3d(0, 0, 0);
    }
  }
  .animate-slideInRight {
    animation: slideInRight 0.5s ease-out forwards;
  }

  @keyframes scaleIn {
    from {
      opacity: 0;
      transform: scale3d(0.9, 0.9, 1);
    }
    to {
      opacity: 1;
      transform: scale3d(1, 1, 1);
    }
  }
  .animate-scaleIn {
    animation: scaleIn 0.3s ease-out forwards;
  }

  @keyframes shimmer {
    0% {
      background-position: -200px 0;
    }
    100% {
      background-position: calc(200px + 100%) 0;
    }
  }
  .animate-shimmer {
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    background-size: 200px 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes pulse {
    0% {
      transform: scale3d(0.95, 0.95, 1);
      box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7);
    }
    70% {
      transform: scale3d(1, 1, 1);
      box-shadow: 0 0 0 6px rgba(52, 211, 153, 0);
    }
    100% {
      transform: scale3d(0.95, 0.95, 1);
      box-shadow: 0 0 0 0 rgba(52, 211, 153, 0);
    }
  }
  
  @keyframes glowPulse {
    0% {
      box-shadow: 0 0 5px 0px rgba(52, 211, 153, 0.7);
    }
    50% {
      box-shadow: 0 0 10px 3px rgba(52, 211, 153, 0.5);
    }
    100% {
      box-shadow: 0 0 5px 0px rgba(52, 211, 153, 0.7);
    }
  }
  
  .animate-status-pulse {
    animation: pulse 2s infinite;
  }
  
  .animate-glow-pulse {
    animation: glowPulse 2s infinite;
  }

  .gpu-accelerated {
    transform: translate3d(0, 0, 0);
    backface-visibility: hidden;
    perspective: 1000px;
  }

  .content-fade-in {
    animation: fadeInUp 0.4s ease-out forwards;
  }

  .hover-lift {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .hover-lift:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  }

  .glass-effect {
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }
`;

// Fast loading skeleton components
const AgentSkeleton = React.memo(() => {
  const { darkMode } = useTheme();
  return (
    <div className={`p-6 rounded-2xl border animate-shimmer hover-lift gpu-accelerated ${
      darkMode ? 'bg-gray-800/50 border-gray-700/50' : 'bg-white/80 border-gray-200/50'
    }`}>
      <div className="flex items-center justify-between mb-4">
        <div className={`h-6 rounded w-3/4 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
        <div className={`w-10 h-10 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
      </div>
      <div className="space-y-3 mb-6">
        <div className={`h-4 rounded w-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
        <div className={`h-4 rounded w-2/3 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
      </div>
      <div className="flex items-center space-x-4 mb-4">
        <div className={`w-8 h-8 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
        <div className={`h-4 rounded w-1/3 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
      </div>
      <div className="flex space-x-2">
        <div className={`h-10 rounded-xl flex-1 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
        <div className={`h-10 rounded-xl flex-1 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}></div>
      </div>
    </div>
  );
});

// Enhanced header component
const AgentsHeader = React.memo(({ 
  agentCount, 
  activeCount 
}: { 
  agentCount: number;
  activeCount: number;
}) => {
  const { darkMode } = useTheme();
  return (
    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-8 content-fade-in">
      <div className="mb-6 lg:mb-0">
        <div className="flex items-center space-x-4 mb-3">
          <div className={`p-3 rounded-2xl ${
            darkMode ? 'bg-blue-900/30 text-blue-400' : 'bg-blue-50 text-blue-600'
          }`}>
            <User size={28} />
          </div>
          <div>
            <h1 className={`text-3xl font-bold ${
              darkMode ? "text-white" : "text-gray-900"
            }`}>
              Agents
            </h1>
            <div className="flex items-center space-x-4 mt-1">
              <div className={`flex items-center space-x-2 text-sm ${
                darkMode ? "text-gray-400" : "text-gray-600"
              }`}>
                <Activity size={16} />
                <span>{agentCount} agents</span>
              </div>
              <div className={`flex items-center space-x-2 text-sm ${
                darkMode ? "text-green-400" : "text-green-600"
              }`}>
                <Bot size={16} />
                <span>{activeCount} active</span>
              </div>
            </div>
          </div>
        </div>
        <p className={`text-lg max-w-2xl ${darkMode ? "text-gray-400" : "text-gray-600"}`}>
          Create and manage intelligent AI agents for your workflows
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <Link href="/agents/create">
          <button className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold transition-all duration-200 hover:from-blue-700 hover:to-blue-800 shadow-lg hover:shadow-xl transform hover:scale-105 gpu-accelerated">
            <div className="flex items-center space-x-2">
              <Plus size={18} />
              <span>Create Agent</span>
            </div>
          </button>
        </Link>
      </div>
    </div>
  );
});

// Enhanced search and filter component
const SearchAndFilter = React.memo(({ 
  searchTerm, 
  setSearchTerm, 
  viewMode, 
  setViewMode,
  darkMode 
}: {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  viewMode: 'grid' | 'list';
  setViewMode: (mode: 'grid' | 'list') => void;
  darkMode: boolean;
}) => {
  return (
    <div className={`rounded-2xl border shadow-xl backdrop-blur-sm p-6 mb-8 content-fade-in glass-effect ${
      darkMode
        ? "bg-gray-800/50 border-gray-700/50"
        : "bg-white/80 border-gray-200/50"
    }`}>
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search size={20} className={darkMode ? "text-gray-400" : "text-gray-500"} />
          </div>
          <input
            type="text"
            placeholder="Search agents..."
            className={`pl-12 pr-4 py-4 w-full rounded-xl border-0 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all duration-200 ${
              darkMode
                ? "bg-gray-900/50 text-white placeholder-gray-400"
                : "bg-gray-50/50 text-gray-900 placeholder-gray-500"
            }`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex items-center space-x-3">
          <div className={`flex rounded-xl border ${
            darkMode ? "border-gray-600 bg-gray-800/50" : "border-gray-300 bg-gray-50/50"
          }`}>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-3 rounded-l-xl transition-all duration-200 ${
                viewMode === 'grid'
                  ? darkMode
                    ? "bg-blue-600 text-white"
                    : "bg-blue-600 text-white"
                  : darkMode
                    ? "text-gray-400 hover:text-gray-300"
                    : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Grid size={18} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-3 rounded-r-xl transition-all duration-200 ${
                viewMode === 'list'
                  ? darkMode
                    ? "bg-blue-600 text-white"
                    : "bg-blue-600 text-white"
                  : darkMode
                    ? "text-gray-400 hover:text-gray-300"
                    : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <List size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

const AgentsPage: NextPage = () => {
  const { darkMode } = useTheme();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  
  // Memoized filtered agents for performance
  const filteredAgents = useMemo(() => {
    if (!searchTerm) return agents;
    return agents.filter(agent =>
      agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (agent.description && agent.description.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  }, [agents, searchTerm]);

  // Memoized active count for performance
  const activeCount = useMemo(() => {
    // Since Agent doesn't have status property, we'll calculate based on other criteria
    // or return 0 for now
    return 0;
  }, [agents]);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await agentService.getAgents();
      setAgents(data);
    } catch (err) {
      console.error('Error fetching agents:', err);
      setError('Failed to load agents. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Function to handle delete button click - directly delete since AgentCard already shows confirmation
  const handleDeleteClick = async (agent: Agent) => {
    try {
      await agentService.deleteAgent(agent.id);
      setAgents(prevAgents => prevAgents.filter(a => a.id !== agent.id));
      toast.success('Agent deleted successfully', {
        style: {
          background: darkMode ? '#1E1E1E' : '#F0FDF4',
          color: darkMode ? '#86EFAC' : '#15803D',
          borderColor: darkMode ? '#166534' : '#DCFCE7',
          borderLeftWidth: '4px',
        },
        icon: '✅'
      });
    } catch (err) {
      console.error('Error deleting agent:', err);
      toast.error('Failed to delete agent', {
        style: {
          background: darkMode ? '#1E1E1E' : '#FEF2F2',
          color: darkMode ? '#F87171' : '#DC2626',
          borderColor: darkMode ? '#DC2626' : '#FECACA',
          borderLeftWidth: '4px',
        },
        icon: '❌'
      });
    }
  };

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  return (
    <MainLayout>
      <style dangerouslySetInnerHTML={{ __html: animationStyles }} />
      <div className={`min-h-screen transition-colors duration-200 ${
        darkMode ? "bg-gray-900" : "bg-gray-50"
      }`}>
        <div className="max-w-7xl mx-auto p-6 space-y-8">
          <AgentsHeader 
            agentCount={agents.length}
            activeCount={activeCount}
          />
          
          <SearchAndFilter 
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            viewMode={viewMode}
            setViewMode={setViewMode}
            darkMode={darkMode}
          />
        
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, index) => (
                <AgentSkeleton key={index} />
            ))}
          </div>
        ) : error ? (
            <div className={`rounded-2xl border shadow-xl p-8 text-center content-fade-in glass-effect ${
              darkMode 
                ? "bg-gray-800/50 border-gray-700/50"
                : "bg-white/80 border-gray-200/50"
            }`}>
              <div className={`inline-flex items-center justify-center w-20 h-20 rounded-full mb-6 ${
                darkMode ? "bg-red-900/30" : "bg-red-100"
              }`}>
                <XCircle size={40} className={darkMode ? "text-red-400" : "text-red-600"} />
              </div>
              <h3 className={`text-2xl font-semibold mb-3 ${
                darkMode ? "text-white" : "text-gray-900"
              }`}>
                Something went wrong
                </h3>
              <p className={`text-lg mb-8 max-w-md mx-auto ${
                darkMode ? "text-gray-400" : "text-gray-600"
              }`}>
                  {error}
                </p>
              <button 
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold transition-all duration-200 hover:from-blue-700 hover:to-blue-800 shadow-lg hover:shadow-xl transform hover:scale-105 gpu-accelerated"
                onClick={fetchAgents}
              >
                <div className="flex items-center space-x-3">
                  <RefreshCcw size={20} />
                  <span>Try Again</span>
                </div>
              </button>
            </div>
          ) : filteredAgents.length === 0 ? (
            searchTerm ? (
              <div className={`rounded-2xl border shadow-xl p-12 text-center content-fade-in glass-effect ${
                  darkMode 
                  ? "bg-gray-800/50 border-gray-700/50"
                  : "bg-white/80 border-gray-200/50"
              }`}>
                <div className={`inline-flex items-center justify-center w-20 h-20 rounded-full mb-6 ${
                  darkMode ? "bg-gray-700/50" : "bg-gray-100"
                }`}>
                  <Search size={40} className={darkMode ? "text-gray-400" : "text-gray-500"} />
            </div>
                <h3 className={`text-2xl font-semibold mb-3 ${
                  darkMode ? "text-white" : "text-gray-900"
                }`}>
                No agents found
              </h3>
                <p className={`text-lg mb-8 max-w-md mx-auto ${
                  darkMode ? "text-gray-400" : "text-gray-600"
                }`}>
                  No agents match your search for "{searchTerm}". Try adjusting your search terms.
                </p>
                <button 
                  onClick={() => setSearchTerm('')}
                  className={`px-6 py-3 border-2 rounded-xl font-medium transition-all duration-200 hover-lift ${
                    darkMode
                      ? "border-gray-600 text-gray-300 hover:bg-gray-700/50 hover:border-gray-500"
                      : "border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400"
                  } shadow-sm hover:shadow-md gpu-accelerated`}
                >
                  Clear Search
                </button>
          </div>
              ) : (
              <div className={`rounded-2xl border shadow-xl p-12 text-center content-fade-in glass-effect ${
            darkMode 
                  ? "bg-gray-800/50 border-gray-700/50"
                  : "bg-white/80 border-gray-200/50"
              }`}>
                <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full mb-8 ${
                  darkMode ? "bg-blue-900/30" : "bg-blue-50"
                }`}>
                  <User size={48} className={darkMode ? "text-blue-400" : "text-blue-600"} />
            </div>
                <h2 className={`text-3xl font-bold mb-4 ${
                  darkMode ? "text-white" : "text-gray-900"
                }`}>
              Create Your First Agent
            </h2>
                <p className={`text-lg mb-8 max-w-2xl mx-auto ${
                  darkMode ? "text-gray-400" : "text-gray-600"
                }`}>
                  You haven't created any agents yet. Create intelligent AI agents to automate tasks and enhance your workflows with powerful AI capabilities.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link href="/agents/create">
                    <button className="px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold transition-all duration-200 hover:from-blue-700 hover:to-blue-800 shadow-lg hover:shadow-xl transform hover:scale-105 gpu-accelerated">
                      <div className="flex items-center space-x-3">
                        <Plus size={20} />
                        <span>Create Agent</span>
                      </div>
                  </button>
                </Link>
                </div>
          </div>
            )
          ) : (
            <div className={`${
              viewMode === 'grid' 
                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' 
                : 'space-y-4'
            }`}>
              {filteredAgents.map((agent, index) => (
                <div
                  key={agent.id}
                  className="animate-slideInRight"
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
              <AgentCard
                agent={agent}
                onDelete={handleDeleteClick}
              />
                </div>
            ))}
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
};

export default AgentsPage; 