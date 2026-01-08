import { useState, Fragment, useMemo } from 'react';
import { Dialog, Transition, Tab } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { useSubtasks, useActivities, useAttachments, useUpdateCard, useKanbanBoard } from '../../hooks/useKanban';
import { SubtaskList } from './SubtaskList';
import { ActivityTimeline } from './ActivityTimeline';
import { AttachmentList } from './AttachmentList';
import { CustomFieldsEditor } from './CustomFieldsEditor';
import { AssigneeSelector } from './AssigneeSelector';
import type { Priority, ApplicationStage, KanbanCard } from '../../types/kanban';

interface CardDetailModalProps {
  applicationId: string;
  onClose: () => void;
}

const PRIORITY_OPTIONS: { value: Priority; label: string; color: string }[] = [
  { value: 'low', label: 'Low', color: 'bg-slate-100 text-slate-700' },
  { value: 'medium', label: 'Medium', color: 'bg-blue-100 text-blue-700' },
  { value: 'high', label: 'High', color: 'bg-amber-100 text-amber-700' },
  { value: 'critical', label: 'Critical', color: 'bg-red-100 text-red-700' },
];

const STAGES: ApplicationStage[] = ['researching', 'writing', 'submitted', 'awarded', 'rejected'];

export function CardDetailModal({ applicationId, onClose }: CardDetailModalProps) {
  const [selectedTab, setSelectedTab] = useState(0);

  const { data: board } = useKanbanBoard();
  const { data: subtasks = [] } = useSubtasks(applicationId);
  const { data: activities = [] } = useActivities(applicationId);
  const { data: attachments = [] } = useAttachments(applicationId);
  const updateCardMutation = useUpdateCard();

  // Find the card in the board
  const card = useMemo(() => {
    if (!board) return null;
    for (const stage of STAGES) {
      const found = board.columns[stage]?.find(
        (c: KanbanCard) => c.id === applicationId
      );
      if (found) return found;
    }
    return null;
  }, [board, applicationId]);

  if (!card) return null;

  const handlePriorityChange = (priority: Priority) => {
    updateCardMutation.mutate({ appId: applicationId, data: { priority } });
  };

  const grantTitle = card.grant?.title || 'Untitled Application';
  const grantAgency = card.grant?.agency || card.grant?.funder_name;

  const tabs = [
    { name: 'Details', count: null },
    { name: 'Subtasks', count: subtasks.length },
    { name: 'Activity', count: activities.length },
    { name: 'Files', count: attachments.length },
  ];

  return (
    <Transition appear show as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl bg-white rounded-xl shadow-xl">
                {/* Header */}
                <div className="flex items-start justify-between p-6 border-b">
                  <div>
                    <Dialog.Title className="text-xl font-semibold text-gray-900">
                      {grantTitle}
                    </Dialog.Title>
                    {grantAgency && (
                      <p className="mt-1 text-sm text-gray-500">{grantAgency}</p>
                    )}
                  </div>
                  <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <XMarkIcon className="w-5 h-5 text-gray-500" />
                  </button>
                </div>

                <div className="flex">
                  {/* Main content */}
                  <div className="flex-1 p-6">
                    <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
                      <Tab.List className="flex space-x-1 border-b mb-6">
                        {tabs.map((tab) => (
                          <Tab
                            key={tab.name}
                            className={({ selected }) =>
                              `px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                selected
                                  ? 'border-blue-500 text-blue-600'
                                  : 'border-transparent text-gray-500 hover:text-gray-700'
                              }`
                            }
                          >
                            {tab.name}
                            {tab.count !== null && tab.count > 0 && (
                              <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-gray-100">
                                {tab.count}
                              </span>
                            )}
                          </Tab>
                        ))}
                      </Tab.List>

                      <Tab.Panels>
                        <Tab.Panel>
                          <CustomFieldsEditor applicationId={applicationId} />
                        </Tab.Panel>
                        <Tab.Panel>
                          <SubtaskList applicationId={applicationId} subtasks={subtasks} />
                        </Tab.Panel>
                        <Tab.Panel>
                          <ActivityTimeline applicationId={applicationId} activities={activities} />
                        </Tab.Panel>
                        <Tab.Panel>
                          <AttachmentList applicationId={applicationId} attachments={attachments} />
                        </Tab.Panel>
                      </Tab.Panels>
                    </Tab.Group>
                  </div>

                  {/* Sidebar */}
                  <div className="w-64 border-l bg-gray-50 p-4 space-y-6">
                    {/* Priority */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-2">
                        Priority
                      </label>
                      <select
                        value={card.priority}
                        onChange={(e) => handlePriorityChange(e.target.value as Priority)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                      >
                        {PRIORITY_OPTIONS.map(opt => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Assignees */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-2">
                        Assignees
                      </label>
                      <AssigneeSelector
                        applicationId={applicationId}
                        currentAssignees={card.assignees || []}
                      />
                    </div>

                    {/* Notes */}
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-2">
                        Notes
                      </label>
                      <textarea
                        value={card.notes || ''}
                        onChange={(e) => updateCardMutation.mutate({
                          appId: applicationId,
                          data: { notes: e.target.value }
                        })}
                        placeholder="Add notes..."
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none"
                      />
                    </div>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}

export default CardDetailModal;
