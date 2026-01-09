import React, { useState, useRef, useEffect } from 'react';
import {
  CheckIcon,
  ChatBubbleLeftIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon } from '@heroicons/react/24/solid';
import type { ChecklistItem as ChecklistItemType, ChecklistCategory } from '../../types/checklists';
import { CHECKLIST_CATEGORY_CONFIGS } from '../../types/checklists';

interface ChecklistItemProps {
  item: ChecklistItemType;
  onToggle: (itemId: string, completed: boolean) => void;
  onUpdateNotes?: (itemId: string, notes: string) => void;
  disabled?: boolean;
  showCategory?: boolean;
  className?: string;
}

function ChecklistItemComponent({
  item,
  onToggle,
  onUpdateNotes,
  disabled = false,
  showCategory = false,
  className = '',
}: ChecklistItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditingNotes, setIsEditingNotes] = useState(false);
  const [notes, setNotes] = useState(item.notes || '');
  const notesInputRef = useRef<HTMLTextAreaElement>(null);

  const categoryConfig = CHECKLIST_CATEGORY_CONFIGS[item.category as ChecklistCategory];

  // Focus notes input when editing
  useEffect(() => {
    if (isEditingNotes && notesInputRef.current) {
      notesInputRef.current.focus();
    }
  }, [isEditingNotes]);

  const handleToggle = () => {
    if (disabled) return;
    onToggle(item.id, !item.completed);
  };

  const handleNotesBlur = () => {
    setIsEditingNotes(false);
    if (notes !== item.notes && onUpdateNotes) {
      onUpdateNotes(item.id, notes);
    }
  };

  const handleNotesKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setNotes(item.notes || '');
      setIsEditingNotes(false);
    }
  };

  const hasDescription = !!item.description;
  const isExpandable = hasDescription || onUpdateNotes;

  const formatDate = (dateString?: string) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  return (
    <div
      className={`group rounded-lg border transition-colors ${
        item.completed
          ? 'border-emerald-200 bg-emerald-50/50'
          : 'border-gray-200 bg-white hover:border-gray-300'
      } ${className}`}
    >
      {/* Main row */}
      <div className="flex items-start gap-3 p-3">
        {/* Checkbox */}
        <button
          type="button"
          onClick={handleToggle}
          disabled={disabled}
          className={`flex-shrink-0 mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center transition-colors ${
            disabled
              ? 'cursor-not-allowed opacity-50'
              : item.completed
              ? 'bg-emerald-500 border-emerald-500 text-white'
              : 'border-gray-300 hover:border-emerald-400 text-transparent hover:text-emerald-400'
          }`}
        >
          <CheckIcon className="w-3 h-3" strokeWidth={3} />
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              {/* Title row */}
              <div className="flex items-center gap-2">
                {isExpandable && (
                  <button
                    type="button"
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex-shrink-0 p-0.5 text-gray-400 hover:text-gray-600 -ml-1"
                  >
                    {isExpanded ? (
                      <ChevronDownIcon className="w-4 h-4" />
                    ) : (
                      <ChevronRightIcon className="w-4 h-4" />
                    )}
                  </button>
                )}
                <span
                  className={`text-sm font-medium ${
                    item.completed ? 'text-gray-500 line-through' : 'text-gray-900'
                  }`}
                >
                  {item.title}
                </span>
              </div>

              {/* Metadata row */}
              <div className="flex items-center gap-2 mt-1">
                {/* Required badge */}
                {item.required && (
                  <span className="inline-flex px-1.5 py-0.5 text-xs font-medium text-rose-700 bg-rose-100 rounded">
                    Required
                  </span>
                )}

                {/* Category badge */}
                {showCategory && categoryConfig && (
                  <span
                    className={`inline-flex px-1.5 py-0.5 text-xs font-medium rounded ${categoryConfig.bgColor} ${categoryConfig.color}`}
                  >
                    {categoryConfig.label}
                  </span>
                )}

                {/* Has notes indicator */}
                {item.notes && !isExpanded && (
                  <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                    <ChatBubbleLeftIcon className="w-3 h-3" />
                  </span>
                )}

                {/* Completed info */}
                {item.completed && item.completed_at && (
                  <span className="text-xs text-gray-400">{formatDate(item.completed_at)}</span>
                )}
              </div>
            </div>

            {/* Weight indicator */}
            {item.weight > 1 && (
              <span className="flex-shrink-0 px-1.5 py-0.5 text-xs font-medium text-slate-600 bg-slate-100 rounded">
                {item.weight}x
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-0 ml-8 space-y-3 border-t border-gray-100 mt-2">
          {/* Description */}
          {hasDescription && (
            <p className="text-sm text-gray-600 pt-3">{item.description}</p>
          )}

          {/* Notes section */}
          {onUpdateNotes && (
            <div className="pt-2">
              <label className="block text-xs font-medium text-gray-500 mb-1">Notes</label>
              {isEditingNotes ? (
                <textarea
                  ref={notesInputRef}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  onBlur={handleNotesBlur}
                  onKeyDown={handleNotesKeyDown}
                  placeholder="Add notes..."
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                />
              ) : (
                <button
                  type="button"
                  onClick={() => setIsEditingNotes(true)}
                  className="w-full text-left px-3 py-2 text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-lg hover:border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  {item.notes || 'Add notes...'}
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Comparison function for React.memo
function areChecklistItemPropsEqual(
  prevProps: ChecklistItemProps,
  nextProps: ChecklistItemProps
): boolean {
  return (
    prevProps.item.id === nextProps.item.id &&
    prevProps.item.completed === nextProps.item.completed &&
    prevProps.item.notes === nextProps.item.notes &&
    prevProps.disabled === nextProps.disabled &&
    prevProps.showCategory === nextProps.showCategory &&
    prevProps.className === nextProps.className
  );
}

export const ChecklistItem = React.memo(ChecklistItemComponent, areChecklistItemPropsEqual);

/**
 * Compact checklist item for inline display
 */
export const ChecklistItemCompact = React.memo(function ChecklistItemCompact({
  item,
  onToggle,
  disabled = false,
  className = '',
}: {
  item: ChecklistItemType;
  onToggle: (itemId: string, completed: boolean) => void;
  disabled?: boolean;
  className?: string;
}) {
  const handleToggle = () => {
    if (disabled) return;
    onToggle(item.id, !item.completed);
  };

  return (
    <div
      className={`flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-50 group ${className}`}
    >
      <button
        type="button"
        onClick={handleToggle}
        disabled={disabled}
        className={`flex-shrink-0 w-4 h-4 rounded border flex items-center justify-center transition-colors ${
          disabled
            ? 'cursor-not-allowed opacity-50'
            : item.completed
            ? 'bg-emerald-500 border-emerald-500 text-white'
            : 'border-gray-300 hover:border-emerald-400'
        }`}
      >
        {item.completed && <CheckIcon className="w-2.5 h-2.5" strokeWidth={3} />}
      </button>
      <span
        className={`flex-1 text-sm ${
          item.completed ? 'text-gray-400 line-through' : 'text-gray-700'
        }`}
      >
        {item.title}
      </span>
      {item.required && !item.completed && (
        <span className="text-xs text-rose-500 font-medium">*</span>
      )}
    </div>
  );
});

/**
 * Read-only checklist item display
 */
export const ChecklistItemReadOnly = React.memo(function ChecklistItemReadOnly({
  item,
  showCategory = false,
  className = '',
}: {
  item: ChecklistItemType;
  showCategory?: boolean;
  className?: string;
}) {
  const categoryConfig = CHECKLIST_CATEGORY_CONFIGS[item.category as ChecklistCategory];

  return (
    <div className={`flex items-start gap-2 py-1 ${className}`}>
      {item.completed ? (
        <CheckCircleIcon className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
      ) : (
        <div className="w-4 h-4 rounded-full border-2 border-gray-300 flex-shrink-0 mt-0.5" />
      )}
      <div className="flex-1 min-w-0">
        <span
          className={`text-sm ${item.completed ? 'text-gray-500 line-through' : 'text-gray-700'}`}
        >
          {item.title}
        </span>
        {showCategory && categoryConfig && (
          <span
            className={`ml-2 inline-flex px-1.5 py-0.5 text-xs font-medium rounded ${categoryConfig.bgColor} ${categoryConfig.color}`}
          >
            {categoryConfig.label}
          </span>
        )}
        {item.required && !item.completed && (
          <span className="ml-1 text-xs text-rose-500 font-medium">Required</span>
        )}
      </div>
    </div>
  );
});

export default ChecklistItem;
