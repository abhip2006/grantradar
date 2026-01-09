import { useNavigate } from 'react-router-dom';
import { NotificationBell } from './NotificationBell';
import {
  useNotifications,
  useMarkAsRead,
  useMarkAllAsRead,
  useDeleteNotification,
} from '../../hooks/useNotifications';
import type { Notification } from '../../types/team';

/**
 * Container component that connects NotificationBell to the notification hooks.
 * This is the component that should be used in the Navbar.
 */
export function NotificationBellContainer() {
  const navigate = useNavigate();
  const { data: notificationsData, isLoading } = useNotifications();
  const markAsRead = useMarkAsRead();
  const markAllAsRead = useMarkAllAsRead();
  const deleteNotification = useDeleteNotification();

  const notifications = notificationsData?.notifications ?? [];

  const handleMarkAsRead = (id: string) => {
    markAsRead.mutate(id);
  };

  const handleMarkAllAsRead = () => {
    markAllAsRead.mutate();
  };

  const handleDelete = (id: string) => {
    deleteNotification.mutate(id);
  };

  const handleNotificationClick = (notification: Notification) => {
    if (notification.action_url) {
      navigate(notification.action_url);
    }
  };

  return (
    <NotificationBell
      notifications={notifications}
      onMarkAsRead={handleMarkAsRead}
      onMarkAllAsRead={handleMarkAllAsRead}
      onDelete={handleDelete}
      onNotificationClick={handleNotificationClick}
      isLoading={isLoading}
    />
  );
}

export default NotificationBellContainer;
