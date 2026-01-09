import { useState } from 'react';
import { Menu, Transition } from '@headlessui/react';
import {
  FunnelIcon,
  UserPlusIcon,
  UserMinusIcon,
  PencilSquareIcon,
  DocumentPlusIcon,
  ArrowRightCircleIcon,
  CheckCircleIcon,
  ChatBubbleLeftIcon,
  ClockIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import type { TeamActivity } from '../../types/team';
import { Fragment } from 'react';

interface ActivityFeedProps {
  activities: TeamActivity[];
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

// Action type configurations
const ACTION_CONFIGS: Record<string, { icon: React.ElementType; color: string; bgColor: string; label: string }> = {
  member_invited: { icon: UserPlusIcon, color: 'text-blue-600', bgColor: 'bg-blue-50', label: 'invited' },
  member_accepted: { icon: CheckCircleIcon, color: 'text-green-600', bgColor: 'bg-green-50', label: 'joined the team' },
  member_removed: { icon: UserMinusIcon, color: 'text-red-600', bgColor: 'bg-red-50', label: 'was removed' },
  member_role_changed: { icon: PencilSquareIcon, color: 'text-purple-600', bgColor: 'bg-purple-50', label: 'role changed' },
  application_created: { icon: DocumentPlusIcon, color: 'text-cyan-600', bgColor: 'bg-cyan-50', label: 'created application' },
  application_stage_changed: { icon: ArrowRightCircleIcon, color: 'text-amber-600', bgColor: 'bg-amber-50', label: 'moved application' },
  application_assigned: { icon: UserPlusIcon, color: 'text-indigo-600', bgColor: 'bg-indigo-50', label: 'assigned to' },
  comment_added: { icon: ChatBubbleLeftIcon, color: 'text-gray-600', bgColor: 'bg-gray-50', label: 'commented on' },
  deadline_updated: { icon: ClockIcon, color: 'text-orange-600', bgColor: 'bg-orange-50', label: 'updated deadline' },
};

const DEFAULT_CONFIG = { icon: PencilSquareIcon, color: 'text-gray-600', bgColor: 'bg-gray-50', label: 'updated' };

// Filter options
const FILTER_OPTIONS = [
  { value: 'all', label: 'All activity' },
  { value: 'member', label: 'Team changes' },
  { value: 'application', label: 'Application updates' },
  { value: 'comment', label: 'Comments' },
];

// Format relative time
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Loading skeleton
function ActivitySkeleton() {
  return (
    <div className="flex gap-3 animate-pulse">
      <div className="w-8 h-8 rounded-lg bg-gray-200 flex-shrink-0" />
      <div className="flex-1">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="h-3 bg-gray-200 rounded w-24" />
      </div>
    </div>
  );
}

export function ActivityFeed({
  activities,
  isLoading = false,
  onLoadMore,
  hasMore = false,
}: ActivityFeedProps) {
  const [filter, setFilter] = useState('all');

  // Filter activities
  const filteredActivities = activities.filter((activity) => {
    if (filter === 'all') return true;
    if (filter === 'member') return activity.action_type.startsWith('member_');
    if (filter === 'application') return activity.action_type.startsWith('application_');
    if (filter === 'comment') return activity.action_type === 'comment_added';
    return true;
  });

  // Group activities by date
  const groupedActivities: Record<string, TeamActivity[]> = {};
  filteredActivities.forEach((activity) => {
    const date = new Date(activity.created_at);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    let dateKey: string;
    if (date.toDateString() === today.toDateString()) {
      dateKey = 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      dateKey = 'Yesterday';
    } else {
      dateKey = date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
    }

    if (!groupedActivities[dateKey]) {
      groupedActivities[dateKey] = [];
    }
    groupedActivities[dateKey].push(activity);
  });

  return (
    <div className="space-y-4">
      {/* Filter dropdown */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">
          {filteredActivities.length} {filteredActivities.length === 1 ? 'activity' : 'activities'}
        </h3>
        <Menu as="div" className="relative">
          <Menu.Button className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-gray-600 hover:bg-gray-100 transition-colors">
            <FunnelIcon className="w-4 h-4" />
            {FILTER_OPTIONS.find((o) => o.value === filter)?.label}
            <ChevronDownIcon className="w-4 h-4" />
          </Menu.Button>
          <Transition
            as={Fragment}
            enter="transition ease-out duration-100"
            enterFrom="transform opacity-0 scale-95"
            enterTo="transform opacity-100 scale-100"
            leave="transition ease-in duration-75"
            leaveFrom="transform opacity-100 scale-100"
            leaveTo="transform opacity-0 scale-95"
          >
            <Menu.Items className="absolute right-0 z-10 mt-2 w-40 origin-top-right rounded-xl bg-white shadow-lg ring-1 ring-black/5 focus:outline-none py-1">
              {FILTER_OPTIONS.map((option) => (
                <Menu.Item key={option.value}>
                  {({ active }) => (
                    <button
                      onClick={() => setFilter(option.value)}
                      className={classNames(
                        active ? 'bg-gray-50' : '',
                        filter === option.value ? 'text-blue-600 font-medium' : 'text-gray-700',
                        'block w-full text-left px-4 py-2 text-sm'
                      )}
                    >
                      {option.label}
                    </button>
                  )}
                </Menu.Item>
              ))}
            </Menu.Items>
          </Transition>
        </Menu>
      </div>

      {/* Loading state */}
      {isLoading && activities.length === 0 && (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <ActivitySkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && filteredActivities.length === 0 && (
        <div className="text-center py-12">
          <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-gray-100 flex items-center justify-center">
            <ClockIcon className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-1">No activity yet</h3>
          <p className="text-sm text-gray-500 max-w-sm mx-auto">
            Team activity will appear here as members collaborate on applications.
          </p>
        </div>
      )}

      {/* Activity timeline */}
      {Object.entries(groupedActivities).map(([dateGroup, groupActivities]) => (
        <div key={dateGroup}>
          <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            {dateGroup}
          </h4>
          <div className="space-y-3">
            {groupActivities.map((activity) => {
              const config = ACTION_CONFIGS[activity.action_type] || DEFAULT_CONFIG;
              const Icon = config.icon;

              return (
                <div key={activity.id} className="flex gap-3 group">
                  {/* Icon */}
                  <div className={classNames(
                    'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                    config.bgColor
                  )}>
                    <Icon className={classNames('w-4 h-4', config.color)} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900">
                      <span className="font-medium">{activity.actor_name || 'Someone'}</span>
                      {' '}
                      <span className="text-gray-600">{config.label}</span>
                      {activity.entity_name && (
                        <>
                          {' '}
                          <span className="font-medium">{activity.entity_name}</span>
                        </>
                      )}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {formatRelativeTime(activity.created_at)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Load more button */}
      {hasMore && onLoadMore && (
        <div className="text-center pt-2">
          <button
            onClick={onLoadMore}
            disabled={isLoading}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            {isLoading ? 'Loading...' : 'Load more activity'}
          </button>
        </div>
      )}
    </div>
  );
}

export default ActivityFeed;
