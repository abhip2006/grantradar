import { useState } from 'react';
import {
  UserPlusIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  UserMinusIcon,
  UserGroupIcon,
  TrashIcon,
  BellIcon,
} from '@heroicons/react/24/outline';
import type { Notification, NotificationType } from '../../types/team';

interface NotificationItemProps {
  notification: Notification;
  onClick: () => void;
  onDelete: () => void;
  compact?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

// Icon and color mapping for notification types
const NOTIFICATION_ICON_MAP: Record<
  NotificationType,
  { icon: React.ComponentType<{ className?: string }>; bgColor: string; iconColor: string }
> = {
  team_invite_received: {
    icon: UserPlusIcon,
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600',
  },
  team_invite_accepted: {
    icon: CheckCircleIcon,
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600',
  },
  team_invite_declined: {
    icon: XCircleIcon,
    bgColor: 'bg-red-100',
    iconColor: 'text-red-600',
  },
  team_role_changed: {
    icon: ArrowPathIcon,
    bgColor: 'bg-yellow-100',
    iconColor: 'text-yellow-600',
  },
  team_member_removed: {
    icon: UserMinusIcon,
    bgColor: 'bg-gray-100',
    iconColor: 'text-gray-600',
  },
  team_member_joined: {
    icon: UserGroupIcon,
    bgColor: 'bg-purple-100',
    iconColor: 'text-purple-600',
  },
};

// Default icon for unknown types
const DEFAULT_ICON = {
  icon: BellIcon,
  bgColor: 'bg-gray-100',
  iconColor: 'text-gray-600',
};

// Format relative time
function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return 'Just now';
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  }

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours}h ago`;
  }

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) {
    return `${diffInDays}d ago`;
  }

  const diffInWeeks = Math.floor(diffInDays / 7);
  if (diffInWeeks < 4) {
    return `${diffInWeeks}w ago`;
  }

  const diffInMonths = Math.floor(diffInDays / 30);
  if (diffInMonths < 12) {
    return `${diffInMonths}mo ago`;
  }

  const diffInYears = Math.floor(diffInDays / 365);
  return `${diffInYears}y ago`;
}

export function NotificationItem({
  notification,
  onClick,
  onDelete,
  compact = false,
}: NotificationItemProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const iconConfig = NOTIFICATION_ICON_MAP[notification.type] || DEFAULT_ICON;
  const IconComponent = iconConfig.icon;

  const handleClick = () => {
    if (!showDeleteConfirm) {
      onClick();
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (showDeleteConfirm) {
      onDelete();
      setShowDeleteConfirm(false);
    } else {
      setShowDeleteConfirm(true);
      // Auto-hide confirm after 3 seconds
      setTimeout(() => setShowDeleteConfirm(false), 3000);
    }
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteConfirm(false);
  };

  return (
    <div
      className={classNames(
        'relative flex items-start gap-3 cursor-pointer transition-colors',
        compact ? 'p-3' : 'p-4',
        notification.read ? 'bg-white' : 'bg-blue-50/50',
        isHovered ? 'bg-gray-50' : ''
      )}
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setShowDeleteConfirm(false);
      }}
    >
      {/* Unread Indicator */}
      {!notification.read && (
        <div className="absolute left-1.5 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-blue-500" />
      )}

      {/* Icon */}
      <div
        className={classNames(
          'flex-shrink-0 rounded-xl flex items-center justify-center',
          compact ? 'w-8 h-8' : 'w-10 h-10',
          iconConfig.bgColor
        )}
      >
        <IconComponent
          className={classNames(compact ? 'w-4 h-4' : 'w-5 h-5', iconConfig.iconColor)}
        />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={classNames(
            'text-gray-900 line-clamp-1',
            compact ? 'text-xs' : 'text-sm',
            notification.read ? 'font-normal' : 'font-medium'
          )}
        >
          {notification.title}
        </p>
        <p
          className={classNames(
            'text-gray-500 line-clamp-2 mt-0.5',
            compact ? 'text-xs' : 'text-sm'
          )}
        >
          {notification.message}
        </p>
        <p className={classNames('text-gray-400 mt-1', compact ? 'text-[10px]' : 'text-xs')}>
          {formatTimeAgo(notification.created_at)}
        </p>
      </div>

      {/* Delete Button - shows on hover */}
      <div
        className={classNames(
          'flex-shrink-0 transition-opacity duration-150',
          isHovered ? 'opacity-100' : 'opacity-0'
        )}
      >
        {showDeleteConfirm ? (
          <div className="flex items-center gap-1">
            <button
              onClick={handleDelete}
              className="px-2 py-1 rounded text-xs font-medium text-white bg-red-500 hover:bg-red-600 transition-colors"
            >
              Delete
            </button>
            <button
              onClick={handleCancelDelete}
              className="px-2 py-1 rounded text-xs font-medium text-gray-600 hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={handleDelete}
            className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
            title="Delete notification"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Action URL indicator */}
      {notification.action_url && (
        <div className="absolute right-4 bottom-3">
          <svg
            className="w-3 h-3 text-gray-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </div>
      )}
    </div>
  );
}

export default NotificationItem;
