import { useState, useEffect } from 'react';
import { KanbanBoard, DeadlineKanbanBoard } from '../components/kanban';
import { PlusIcon, Squares2X2Icon, CalendarDaysIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

type BoardTab = 'applications' | 'deadlines';

const TABS = [
  { id: 'applications' as const, label: 'Applications', icon: DocumentTextIcon, description: 'Track grant applications' },
  { id: 'deadlines' as const, label: 'Deadlines', icon: CalendarDaysIcon, description: 'Manage deadline workflow' },
];

export function Kanban() {
  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState<BoardTab>('applications');

  useEffect(() => {
    setMounted(true);
  }, []);

  const activeTabInfo = TABS.find(t => t.id === activeTab);

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-mesh">
      {/* Premium Page Header */}
      <div className="analytics-header">
        <div className="px-6 py-5">
          <div className={`flex items-center justify-between ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-100 to-blue-50 flex items-center justify-center shadow-sm">
                <Squares2X2Icon className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-display font-semibold text-gray-900">
                    Workflow Board
                  </h1>
                  <span className="live-indicator text-sm text-gray-500 font-medium">
                    Live
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-0.5">
                  {activeTabInfo?.description || 'Manage your grant workflow'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Tab Switcher */}
              <div className="flex bg-gray-100/80 p-1 rounded-xl">
                {TABS.map((tab) => {
                  const isActive = activeTab === tab.id;
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`
                        flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                        ${isActive
                          ? 'bg-white text-gray-900 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                        }
                      `}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Add Button */}
              <button className="group inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-semibold hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg shadow-blue-500/25 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-blue-500/30">
                <PlusIcon className="w-4 h-4 transition-transform group-hover:rotate-90" />
                {activeTab === 'applications' ? 'Add Application' : 'Add Deadline'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Board content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'applications' ? (
          <KanbanBoard />
        ) : (
          <DeadlineKanbanBoard />
        )}
      </div>
    </div>
  );
}

export default Kanban;
