import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import type { Deadline } from '../../types';
import type { EventClickArg } from '@fullcalendar/core';

interface DeadlinesCalendarProps {
  deadlines: Deadline[];
  onEdit: (deadline: Deadline) => void;
}

export function DeadlinesCalendar({ deadlines, onEdit }: DeadlinesCalendarProps) {
  const events = deadlines.map(d => ({
    id: d.id,
    title: d.title,
    start: d.sponsor_deadline,
    backgroundColor: d.is_overdue ? '#EF4444' : d.color,
    borderColor: d.is_overdue ? '#DC2626' : d.color,
    extendedProps: { deadline: d },
  }));

  const handleEventClick = (info: EventClickArg) => {
    const deadline = info.event.extendedProps.deadline as Deadline;
    if (deadline) {
      onEdit(deadline);
    }
  };

  return (
    <div className="bg-white shadow rounded-lg p-4">
      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={events}
        eventClick={handleEventClick}
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,dayGridWeek'
        }}
        height="auto"
        eventDisplay="block"
        dayMaxEvents={3}
      />
    </div>
  );
}
