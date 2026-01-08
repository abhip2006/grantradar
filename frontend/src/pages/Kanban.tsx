import { KanbanBoard } from '../components/kanban';

export function Kanban() {
  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-gray-100">
      {/* Page header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Application Board</h1>
            <p className="text-sm text-gray-500 mt-1">
              Track and manage your grant applications
            </p>
          </div>

          {/* Optional: Add application button */}
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
            Add Application
          </button>
        </div>
      </div>

      {/* Kanban board */}
      <div className="flex-1 overflow-hidden">
        <KanbanBoard />
      </div>
    </div>
  );
}

export default Kanban;
