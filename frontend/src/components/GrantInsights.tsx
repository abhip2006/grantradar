import { useState, useRef, useCallback } from 'react';
import {
  SparklesIcon,
  ShieldCheckIcon,
  PencilSquareIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

interface GrantInsightsProps {
  grantId: string;
  grantTitle: string;
  funderName?: string;
}

type InsightStatus = 'idle' | 'loading' | 'done' | 'error';
type ActiveTab = 'eligibility' | 'writing';

// Simple markdown renderer for AI-generated content
function renderMarkdown(text: string): JSX.Element {
  if (!text) return <></>;

  const lines = text.split('\n');
  const elements: JSX.Element[] = [];
  let listItems: string[] = [];
  let inList = false;

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="list-disc list-inside space-y-1 mb-4 text-gray-700">
          {listItems.map((item, i) => (
            <li key={i}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
    inList = false;
  };

  lines.forEach((line, index) => {
    // Headers
    if (line.startsWith('## ')) {
      flushList();
      elements.push(
        <h2 key={index} className="text-lg font-semibold text-gray-900 mt-6 mb-3 first:mt-0">
          {renderInlineMarkdown(line.slice(3))}
        </h2>
      );
    } else if (line.startsWith('### ')) {
      flushList();
      elements.push(
        <h3 key={index} className="text-base font-semibold text-gray-800 mt-4 mb-2">
          {renderInlineMarkdown(line.slice(4))}
        </h3>
      );
    }
    // Bullet points
    else if (line.match(/^[-*]\s/)) {
      inList = true;
      listItems.push(line.slice(2));
    }
    // Numbered lists
    else if (line.match(/^\d+\.\s/)) {
      inList = true;
      listItems.push(line.replace(/^\d+\.\s/, ''));
    }
    // Empty line
    else if (line.trim() === '') {
      flushList();
    }
    // Regular paragraph
    else {
      flushList();
      elements.push(
        <p key={index} className="text-gray-700 mb-3 leading-relaxed">
          {renderInlineMarkdown(line)}
        </p>
      );
    }
  });

  flushList();
  return <>{elements}</>;
}

// Render inline markdown (bold, italic)
function renderInlineMarkdown(text: string): JSX.Element {
  // Handle **bold** text
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={i} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

export function GrantInsights({ grantId, grantTitle, funderName }: GrantInsightsProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>('eligibility');
  const [isGenerating, setIsGenerating] = useState(false);
  const [eligibilityContent, setEligibilityContent] = useState('');
  const [writingContent, setWritingContent] = useState('');
  const [eligibilityStatus, setEligibilityStatus] = useState<InsightStatus>('idle');
  const [writingStatus, setWritingStatus] = useState<InsightStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const generateInsights = useCallback(async () => {
    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Reset state
    setIsGenerating(true);
    setEligibilityContent('');
    setWritingContent('');
    setEligibilityStatus('idle');
    setWritingStatus('idle');
    setError(null);

    // Create abort controller
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(
        `http://localhost:8000/api/insights/grant/${grantId}/stream?insight_type=both`,
        {
          signal: abortControllerRef.current.signal,
          headers: {
            'Accept': 'text/event-stream',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        let eventType = '';
        let eventData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            eventData = line.slice(6);

            // Process the event
            if (eventType && eventData) {
              try {
                const data = JSON.parse(eventData);
                handleSSEEvent(eventType, data);
              } catch {
                // Ignore JSON parse errors for empty data
              }
              eventType = '';
              eventData = '';
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        // Request was cancelled, ignore
        return;
      }
      console.error('Failed to generate insights:', err);
      setError((err as Error).message);
      setEligibilityStatus('error');
      setWritingStatus('error');
    } finally {
      setIsGenerating(false);
    }
  }, [grantId]);

  const handleSSEEvent = (eventType: string, data: { content?: string; message?: string }) => {
    switch (eventType) {
      case 'eligibility_start':
        setEligibilityStatus('loading');
        setActiveTab('eligibility');
        break;
      case 'eligibility_chunk':
        if (data.content) {
          setEligibilityContent(prev => prev + data.content);
        }
        break;
      case 'eligibility_end':
        setEligibilityStatus('done');
        break;
      case 'writing_start':
        setWritingStatus('loading');
        break;
      case 'writing_chunk':
        if (data.content) {
          setWritingContent(prev => prev + data.content);
        }
        break;
      case 'writing_end':
        setWritingStatus('done');
        break;
      case 'error':
        setError(data.message || 'An error occurred');
        break;
    }
  };

  const getStatusIcon = (status: InsightStatus) => {
    switch (status) {
      case 'loading':
        return <ArrowPathIcon className="h-4 w-4 animate-spin" />;
      case 'done':
        return <span className="h-2 w-2 rounded-full bg-emerald-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <section className="grant-insights-section bg-gradient-to-br from-violet-50 via-violet-50/80 to-indigo-50 rounded-2xl border border-violet-100 shadow-sm overflow-hidden animate-fade-in-up">
      {/* Header */}
      <div className="p-6 pb-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-lg shadow-violet-200">
              <SparklesIcon className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                AI Grant Insights
              </h2>
              <p className="text-sm text-violet-600/80">
                Personalized analysis powered by Claude
              </p>
            </div>
          </div>

          <button
            onClick={generateInsights}
            disabled={isGenerating}
            className={`
              inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm
              transition-all duration-200 shadow-sm
              ${isGenerating
                ? 'bg-violet-100 text-violet-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 hover:shadow-md hover:shadow-violet-200'
              }
            `}
          >
            {isGenerating ? (
              <>
                <ArrowPathIcon className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <SparklesIcon className="h-4 w-4" />
                Generate Insights
              </>
            )}
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="px-6 flex gap-2">
        <button
          onClick={() => setActiveTab('eligibility')}
          className={`
            inline-flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-sm
            transition-colors duration-150 border-b-2
            ${activeTab === 'eligibility'
              ? 'bg-white text-violet-700 border-violet-500 shadow-sm'
              : 'text-gray-500 hover:text-gray-700 border-transparent hover:bg-white/50'
            }
          `}
        >
          <ShieldCheckIcon className="h-4 w-4" />
          Eligibility Analysis
          {getStatusIcon(eligibilityStatus)}
        </button>
        <button
          onClick={() => setActiveTab('writing')}
          className={`
            inline-flex items-center gap-2 px-4 py-2.5 rounded-t-lg font-medium text-sm
            transition-colors duration-150 border-b-2
            ${activeTab === 'writing'
              ? 'bg-white text-violet-700 border-violet-500 shadow-sm'
              : 'text-gray-500 hover:text-gray-700 border-transparent hover:bg-white/50'
            }
          `}
        >
          <PencilSquareIcon className="h-4 w-4" />
          Writing Tips
          {getStatusIcon(writingStatus)}
        </button>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-b-xl mx-0 p-6 min-h-[250px] border-t border-violet-100">
        {error && (
          <div className="mb-4 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-center gap-2">
            <ExclamationTriangleIcon className="h-5 w-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {activeTab === 'eligibility' ? (
          <InsightContent
            content={eligibilityContent}
            status={eligibilityStatus}
            placeholder="Click 'Generate Insights' to analyze your eligibility for this grant based on your profile..."
          />
        ) : (
          <InsightContent
            content={writingContent}
            status={writingStatus}
            placeholder="Click 'Generate Insights' to get personalized writing tips for this grant application..."
          />
        )}
      </div>
    </section>
  );
}

interface InsightContentProps {
  content: string;
  status: InsightStatus;
  placeholder: string;
}

function InsightContent({ content, status, placeholder }: InsightContentProps) {
  // Idle state with no content
  if (status === 'idle' && !content) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="p-4 rounded-full bg-violet-100 mb-4">
          <SparklesIcon className="h-8 w-8 text-violet-400" />
        </div>
        <p className="text-gray-400 max-w-md">{placeholder}</p>
      </div>
    );
  }

  // Loading state with no content yet
  if (status === 'loading' && !content) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-4 bg-violet-100 rounded w-1/4" />
        <div className="h-4 bg-violet-50 rounded w-3/4" />
        <div className="h-4 bg-violet-50 rounded w-2/3" />
        <div className="h-4 bg-violet-50 rounded w-5/6" />
        <div className="h-4 bg-violet-100 rounded w-1/3 mt-6" />
        <div className="h-4 bg-violet-50 rounded w-4/5" />
        <div className="h-4 bg-violet-50 rounded w-3/4" />
      </div>
    );
  }

  // Content with optional streaming cursor
  return (
    <div className="prose-violet max-w-none">
      {renderMarkdown(content)}
      {status === 'loading' && (
        <span className="inline-block w-2 h-5 bg-violet-500 animate-pulse ml-0.5 -mb-1 rounded-sm" />
      )}
    </div>
  );
}

export default GrantInsights;
