import React, { useState, Fragment } from 'react';
import {
  DocumentDuplicateIcon,
  PencilIcon,
  TrashIcon,
  EllipsisVerticalIcon,
  ClockIcon,
  DocumentTextIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import { Menu, Transition } from '@headlessui/react';
import type { DocumentComponent, ComponentCategory } from '../../types/components';
import { COMPONENT_CATEGORY_CONFIG } from '../../types/components';

interface ComponentCardProps {
  component: DocumentComponent;
  onEdit: (component: DocumentComponent) => void;
  onDelete: (component: DocumentComponent) => void;
  onDuplicate: (component: DocumentComponent) => void;
  onPreview: (component: DocumentComponent) => void;
  onInsert?: (component: DocumentComponent) => void;
  showInsertButton?: boolean;
}

export const ComponentCard = React.memo(function ComponentCard({
  component,
  onEdit,
  onDelete,
  onDuplicate,
  onPreview,
  onInsert,
  showInsertButton = false,
}: ComponentCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  const categoryConfig = COMPONENT_CATEGORY_CONFIG[component.category as ComponentCategory] ||
    COMPONENT_CATEGORY_CONFIG.other;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const truncateContent = (content: string, maxLength: number = 150) => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength).trim() + '...';
  };

  const getWordCount = (content: string) => {
    return content.split(/\s+/).filter(Boolean).length;
  };

  return (
    <div
      className="group relative bg-[var(--gr-bg-elevated)] border border-[var(--gr-border-subtle)] rounded-xl p-4 hover:border-[var(--gr-border-default)] hover:shadow-[var(--gr-shadow-md)] transition-all duration-200"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-secondary)]">
              {categoryConfig.label}
            </span>
            {component.version > 1 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--gr-blue-100)] text-[var(--gr-blue-700)]">
                v{component.version}
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-[var(--gr-text-primary)] truncate pr-2">
            {component.name}
          </h3>
        </div>

        {/* Actions Menu */}
        <Menu as="div" className="relative">
          <Menu.Button className="p-1 text-[var(--gr-text-tertiary)] hover:text-[var(--gr-text-primary)] hover:bg-[var(--gr-bg-tertiary)] rounded-lg transition-colors">
            <EllipsisVerticalIcon className="h-5 w-5" />
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
            <Menu.Items className="absolute right-0 mt-1 w-48 origin-top-right bg-[var(--gr-bg-elevated)] border border-[var(--gr-border-default)] rounded-lg shadow-[var(--gr-shadow-lg)] py-1 z-10">
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={() => onPreview(component)}
                    className={`${
                      active ? 'bg-[var(--gr-bg-tertiary)]' : ''
                    } flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--gr-text-primary)]`}
                  >
                    <EyeIcon className="h-4 w-4" />
                    Preview
                  </button>
                )}
              </Menu.Item>
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={() => onEdit(component)}
                    className={`${
                      active ? 'bg-[var(--gr-bg-tertiary)]' : ''
                    } flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--gr-text-primary)]`}
                  >
                    <PencilIcon className="h-4 w-4" />
                    Edit
                  </button>
                )}
              </Menu.Item>
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={() => onDuplicate(component)}
                    className={`${
                      active ? 'bg-[var(--gr-bg-tertiary)]' : ''
                    } flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--gr-text-primary)]`}
                  >
                    <DocumentDuplicateIcon className="h-4 w-4" />
                    Duplicate
                  </button>
                )}
              </Menu.Item>
              <div className="my-1 border-t border-[var(--gr-border-subtle)]" />
              <Menu.Item>
                {({ active }) => (
                  <button
                    onClick={() => onDelete(component)}
                    className={`${
                      active ? 'bg-red-50' : ''
                    } flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600`}
                  >
                    <TrashIcon className="h-4 w-4" />
                    Delete
                  </button>
                )}
              </Menu.Item>
            </Menu.Items>
          </Transition>
        </Menu>
      </div>

      {/* Content Preview */}
      <div className="mb-3">
        <p className="text-sm text-[var(--gr-text-secondary)] line-clamp-3">
          {truncateContent(component.content)}
        </p>
      </div>

      {/* Metadata */}
      <div className="flex items-center gap-4 text-xs text-[var(--gr-text-tertiary)]">
        <div className="flex items-center gap-1">
          <DocumentTextIcon className="h-3.5 w-3.5" />
          <span>{getWordCount(component.content)} words</span>
        </div>
        <div className="flex items-center gap-1">
          <ClockIcon className="h-3.5 w-3.5" />
          <span>{formatDate(component.updated_at)}</span>
        </div>
      </div>

      {/* Tags from metadata */}
      {component.metadata?.tags && component.metadata.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {component.metadata.tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="inline-flex px-2 py-0.5 rounded text-xs bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-tertiary)]"
            >
              {tag}
            </span>
          ))}
          {component.metadata.tags.length > 3 && (
            <span className="inline-flex px-2 py-0.5 rounded text-xs bg-[var(--gr-bg-tertiary)] text-[var(--gr-text-tertiary)]">
              +{component.metadata.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Insert Button (shown when in insert mode) */}
      {showInsertButton && onInsert && (
        <div className="mt-4 pt-3 border-t border-[var(--gr-border-subtle)]">
          <button
            onClick={() => onInsert(component)}
            className="w-full btn-primary text-sm py-2"
          >
            Insert Component
          </button>
        </div>
      )}

      {/* Quick Preview Overlay on Hover */}
      {isHovered && !showInsertButton && (
        <div className="absolute inset-x-0 bottom-0 p-4 pt-8 bg-gradient-to-t from-[var(--gr-bg-elevated)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onPreview(component)}
            className="w-full btn-secondary text-sm py-2"
          >
            Quick Preview
          </button>
        </div>
      )}
    </div>
  );
});

export default ComponentCard;
