import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi, researchApi, alertsApi } from '../services/api';
import type { ChatSessionListItem, ResearchSession, AlertFrequency } from '../types';

type Tab = 'chat' | 'research' | 'alerts';

export function AITools() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">AI Tools</h1>
        <p className="mt-2 text-gray-600">
          Intelligent tools to help you discover and apply for grants
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('chat')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'chat'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Chat Assistant
          </button>
          <button
            onClick={() => setActiveTab('research')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'research'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Deep Research
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'alerts'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Funding Alerts
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'chat' && <ChatTab />}
      {activeTab === 'research' && <ResearchTab />}
      {activeTab === 'alerts' && <AlertsTab />}
    </div>
  );
}

function ChatTab() {
  const queryClient = useQueryClient();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  const { data: sessions = [] } = useQuery({
    queryKey: ['chatSessions'],
    queryFn: () => chatApi.getSessions(),
  });

  const { data: currentSession, isLoading: sessionLoading } = useQuery({
    queryKey: ['chatSession', selectedSessionId],
    queryFn: () => chatApi.getSession(selectedSessionId!),
    enabled: !!selectedSessionId,
  });

  const createSession = useMutation({
    mutationFn: () => chatApi.createSession({ session_type: 'proposal_chat' }),
    onSuccess: (session) => {
      setSelectedSessionId(session.id);
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
    },
  });

  const sendMessage = useMutation({
    mutationFn: (content: string) => chatApi.sendMessage(selectedSessionId!, content),
    onSuccess: () => {
      setMessage('');
      queryClient.invalidateQueries({ queryKey: ['chatSession', selectedSessionId] });
    },
  });

  const handleSend = () => {
    if (message.trim() && selectedSessionId) {
      sendMessage.mutate(message);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Sessions Sidebar */}
      <div className="lg:col-span-1 bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-gray-900">Conversations</h3>
          <button
            onClick={() => createSession.mutate()}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            + New
          </button>
        </div>
        <div className="space-y-2">
          {sessions.map((s: ChatSessionListItem) => (
            <button
              key={s.id}
              onClick={() => setSelectedSessionId(s.id)}
              className={`w-full text-left p-3 rounded-lg text-sm ${
                selectedSessionId === s.id
                  ? 'bg-blue-50 text-blue-700'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <div className="font-medium truncate">{s.title}</div>
              <div className="text-xs text-gray-500">{s.message_count} messages</div>
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-4">
              No conversations yet
            </p>
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="lg:col-span-3 bg-white rounded-lg shadow flex flex-col h-[600px]">
        {selectedSessionId ? (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {sessionLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                currentSession?.messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg p-3 ${
                        msg.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-gray-200">
                          <p className="text-xs font-medium mb-1">Sources:</p>
                          {msg.sources.map((s, i) => (
                            <p key={i} className="text-xs opacity-80">
                              {s.title}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Input */}
            <div className="border-t p-4">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask about grants, eligibility, or proposals..."
                  className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={sendMessage.isPending}
                />
                <button
                  onClick={handleSend}
                  disabled={sendMessage.isPending || !message.trim()}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {sendMessage.isPending ? 'Sending...' : 'Send'}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">Select a conversation or start a new one</p>
              <button
                onClick={() => createSession.mutate()}
                className="text-blue-600 hover:text-blue-700"
              >
                Start New Conversation
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ResearchTab() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  const { data: sessions = [] } = useQuery({
    queryKey: ['researchSessions'],
    queryFn: () => researchApi.getSessions(),
  });

  const { data: currentSession, isLoading: sessionLoading } = useQuery({
    queryKey: ['researchSession', selectedSessionId],
    queryFn: () => researchApi.getSession(selectedSessionId!),
    enabled: !!selectedSessionId,
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' || query.state.data?.status === 'processing' ? 2000 : false,
  });

  const startResearch = useMutation({
    mutationFn: (query: string) => researchApi.createSession(query),
    onSuccess: (session) => {
      setSelectedSessionId(session.id);
      setQuery('');
      queryClient.invalidateQueries({ queryKey: ['researchSessions'] });
    },
  });

  const handleStartResearch = () => {
    if (query.trim().length >= 10) {
      startResearch.mutate(query);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Input */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Deep Research</h3>
        <p className="text-gray-600 mb-4">
          Describe your research interests and goals. Our AI will find the most relevant funding opportunities.
        </p>
        <div className="flex gap-2">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., I'm researching CRISPR-based therapies for rare genetic diseases. I'm an early-career investigator at a US academic institution..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
          />
        </div>
        <button
          onClick={handleStartResearch}
          disabled={startResearch.isPending || query.length < 10}
          className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {startResearch.isPending ? 'Starting Research...' : 'Start Deep Research'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Past Sessions */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-gray-900 mb-4">Research History</h3>
          <div className="space-y-2">
            {sessions.map((s: ResearchSession) => (
              <button
                key={s.id}
                onClick={() => setSelectedSessionId(s.id)}
                className={`w-full text-left p-3 rounded-lg text-sm ${
                  selectedSessionId === s.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                <div className="font-medium truncate">{s.query.slice(0, 50)}...</div>
                <div className="flex justify-between text-xs text-gray-500">
                  <span className={`capitalize ${
                    s.status === 'completed' ? 'text-green-600' :
                    s.status === 'processing' ? 'text-yellow-600' :
                    s.status === 'failed' ? 'text-red-600' : ''
                  }`}>
                    {s.status}
                  </span>
                  <span>{s.grants_found ?? 0} grants</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-gray-900 mb-4">Results</h3>
          {sessionLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : currentSession ? (
            <div className="space-y-4">
              {currentSession.status === 'processing' && (
                <div className="flex items-center gap-2 text-yellow-600 bg-yellow-50 p-3 rounded-lg">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600"></div>
                  <span>Researching... This may take a minute.</span>
                </div>
              )}

              {currentSession.insights && (
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium text-blue-900 mb-2">AI Insights</h4>
                  <p className="text-blue-800 whitespace-pre-wrap">{currentSession.insights}</p>
                </div>
              )}

              {currentSession.results && currentSession.results.length > 0 && (
                <div className="space-y-3">
                  {currentSession.results.map((grant) => (
                    <div key={grant.id} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <h4 className="font-medium text-gray-900">{grant.title}</h4>
                        <span className="text-sm font-medium text-blue-600">
                          {Math.round(grant.relevance_score * 100)}% match
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1">
                        {grant.funder} {grant.mechanism && `| ${grant.mechanism}`}
                      </p>
                      <p className="text-sm text-gray-500 mt-2 line-clamp-2">
                        {grant.description}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {grant.match_reasons.map((reason, i) => (
                          <span
                            key={i}
                            className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded"
                          >
                            {reason}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              Select a research session or start a new search
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function AlertsTab() {
  const queryClient = useQueryClient();

  const { data: preferences, isLoading } = useQuery({
    queryKey: ['alertPreferences'],
    queryFn: () => alertsApi.getPreferences(),
  });

  const updatePreferences = useMutation({
    mutationFn: alertsApi.updatePreferences,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alertPreferences'] }),
  });

  const sendNow = useMutation({
    mutationFn: alertsApi.sendNow,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-900 mb-6">Funding Alert Preferences</h3>

        <div className="space-y-6">
          {/* Enable/Disable */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">Enable Alerts</p>
              <p className="text-sm text-gray-500">Receive personalized funding alerts via email</p>
            </div>
            <button
              onClick={() => updatePreferences.mutate({ enabled: !preferences?.enabled })}
              className={`relative inline-flex h-6 w-11 items-center rounded-full ${
                preferences?.enabled ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                  preferences?.enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Frequency */}
          <div>
            <p className="font-medium text-gray-900 mb-2">Frequency</p>
            <select
              value={preferences?.frequency || 'weekly'}
              onChange={(e) => updatePreferences.mutate({ frequency: e.target.value as AlertFrequency })}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>

          {/* Minimum Match Score */}
          <div>
            <p className="font-medium text-gray-900 mb-2">
              Minimum Match Score: {preferences?.min_match_score || 70}%
            </p>
            <input
              type="range"
              min="50"
              max="95"
              value={preferences?.min_match_score || 70}
              onChange={(e) => updatePreferences.mutate({ min_match_score: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>

          {/* Include Options */}
          <div className="space-y-3">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={preferences?.include_new_grants ?? true}
                onChange={(e) => updatePreferences.mutate({ include_new_grants: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Include new matching grants</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={preferences?.include_deadlines ?? true}
                onChange={(e) => updatePreferences.mutate({ include_deadlines: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Include upcoming deadlines</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={preferences?.include_insights ?? true}
                onChange={(e) => updatePreferences.mutate({ include_insights: e.target.checked })}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Include AI insights</span>
            </label>
          </div>

          {/* Send Now Button */}
          <div className="pt-4 border-t">
            <button
              onClick={() => sendNow.mutate()}
              disabled={sendNow.isPending}
              className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 disabled:opacity-50"
            >
              {sendNow.isPending ? 'Sending...' : 'Send Test Alert Now'}
            </button>
            {sendNow.isSuccess && (
              <p className="text-sm text-green-600 mt-2">Alert sent! Check your email.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AITools;
