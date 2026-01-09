import { Fragment, useState } from 'react';
import { Popover, Transition } from '@headlessui/react';
import {
  BellIcon,
  CheckIcon,
  InboxIcon,
} from '@heroicons/react/24/outline';
import { BellIcon as BellSolidIcon } from '@heroicons/react/24/solid';
import { NotificationItem } from './NotificationItem';
import type { Notification } from '../../types/team';

interface NotificationBellProps {
  notifications: Notification[];
  onMarkAsRead: (id: string) => void;
  onMarkAllAsRead: () => void;
  onDelete: (id: string) => void;
  onNotificationClick?: (notification: Notification) => void;
  notificationsPageUrl?: string;
  isLoading?: boolean;
}

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export function NotificationBell({
  notifications,
  onMarkAsRead,
  onMarkAllAsRead,
  onDelete,
  onNotificationClick,
  notificationsPageUrl = '/notifications',
  isLoading = false,
}: NotificationBellProps) {
  const [isHovered, setIsHovered] = useState(false);

  const unreadCount = notifications.filter((n) => !n.read).length;
  const hasUnread = unreadCount > 0;

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      onMarkAsRead(notification.id);
    }
    if (onNotificationClick) {
      onNotificationClick(notification);
    }
  };

  return (
    <Popover className="relative">
      {({ open }) => (
        <>
          <Popover.Button
            className={classNames(
              'relative p-2 rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
              open || isHovered
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
            )}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
          >
            {/* Bell Icon */}
            {hasUnread && !open ? (
              <BellSolidIcon className="w-6 h-6" />
            ) : (
              <BellIcon className="w-6 h-6" />
            )}

            {/* Unread Badge */}
            {hasUnread && (
              <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-xs font-semibold shadow-sm animate-pulse">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </Popover.Button>

          <Transition
            as={Fragment}
            enter="transition ease-out duration-200"
            enterFrom="opacity-0 translate-y-1"
            enterTo="opacity-100 translate-y-0"
            leave="transition ease-in duration-150"
            leaveFrom="opacity-100 translate-y-0"
            leaveTo="opacity-0 translate-y-1"
          >
            <Popover.Panel className="absolute right-0 z-50 mt-2 w-96 origin-top-right">
              <div className="overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-black/5">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
                    {hasUnread && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  {hasUnread && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onMarkAllAsRead();
                      }}
                      className="flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      <CheckIcon className="w-3.5 h-3.5" />
                      Mark all as read
                    </button>
                  )}
                </div>

                {/* Notifications List */}
                <div className="max-h-[400px] overflow-y-auto">
                  {isLoading ? (
                    // Loading skeleton
                    <div className="p-4 space-y-3">
                      {[...Array(3)].map((_, i) => (
                        <div key={i} className="flex items-start gap-3 animate-pulse">
                          <div className="w-10 h-10 rounded-xl bg-gray-200" />
                          <div className="flex-1">
                            <div className="h-4 w-3/4 bg-gray-200 rounded mb-2" />
                            <div className="h-3 w-full bg-gray-200 rounded" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : notifications.length === 0 ? (
                    // Empty state
                    <div className="py-12 px-4 text-center">
                      <InboxIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <h4 className="text-sm font-medium text-gray-900 mb-1">
                        No notifications
                      </h4>
                      <p className="text-xs text-gray-500">
                        You're all caught up! New notifications will appear here.
                      </p>
                    </div>
                  ) : (
                    // Notification items
                    <div className="divide-y divide-gray-100">
                      {notifications.map((notification) => (
                        <NotificationItem
                          key={notification.id}
                          notification={notification}
                          onClick={() => handleNotificationClick(notification)}
                          onDelete={() => onDelete(notification.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer - View All Link */}
                {notifications.length > 0 && (
                  <div className="px-4 py-3 border-t border-gray-100 bg-gray-50">
                    <a
                      href={notificationsPageUrl}
                      className="block w-full text-center text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      View all notifications
                    </a>
                  </div>
                )}
              </div>
            </Popover.Panel>
          </Transition>
        </>
      )}
    </Popover>
  );
}

export default NotificationBell;
