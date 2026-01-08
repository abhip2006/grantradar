import React, { useRef } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { useUploadAttachment, useDeleteAttachment } from '../../hooks/useKanban';
import { kanbanApi } from '../../services/api';
import type { Attachment } from '../../types/kanban';
import {
  PaperClipIcon,
  ArrowDownTrayIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';

interface AttachmentListProps {
  applicationId: string;
  attachments: Attachment[];
}

const FILE_ICONS: Record<string, string> = {
  'application/pdf': 'PDF',
  'image/png': 'PNG',
  'image/jpeg': 'JPG',
  'application/msword': 'DOC',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
  'application/vnd.ms-excel': 'XLS',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
  'text/plain': 'TXT',
};

export function AttachmentList({ applicationId, attachments }: AttachmentListProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadAttachment();
  const deleteMutation = useDeleteAttachment();

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    uploadMutation.mutate({ appId: applicationId, file });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDownload = async (attachment: Attachment) => {
    try {
      const blob = await kanbanApi.downloadAttachment(attachment.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = attachment.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (fileType?: string): string => {
    if (!fileType) return 'FILE';
    return FILE_ICONS[fileType] || 'FILE';
  };

  return (
    <div className="space-y-4">
      {/* Upload button */}
      <div>
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleUpload}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          <PaperClipIcon className="w-4 h-4" />
          {uploadMutation.isPending ? 'Uploading...' : 'Attach file'}
        </button>
      </div>

      {/* File list */}
      <div className="space-y-2">
        {attachments.map((attachment) => (
          <div
            key={attachment.id}
            className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-gray-300 group"
          >
            <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center text-xs font-semibold text-gray-500">
              {getFileIcon(attachment.file_type)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {attachment.filename}
              </p>
              <p className="text-xs text-gray-500">
                {formatFileSize(attachment.file_size)}
                {attachment.file_size && ' - '}
                {formatDistanceToNow(new Date(attachment.created_at), { addSuffix: true })}
              </p>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => handleDownload(attachment)}
                className="p-2 text-gray-400 hover:text-blue-600 rounded"
                title="Download"
              >
                <ArrowDownTrayIcon className="w-4 h-4" />
              </button>
              <button
                onClick={() => deleteMutation.mutate(attachment.id)}
                className="p-2 text-gray-400 hover:text-red-600 rounded"
                title="Delete"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}

        {attachments.length === 0 && (
          <p className="text-center text-gray-400 py-8 text-sm">
            No files attached
          </p>
        )}
      </div>
    </div>
  );
}

export default AttachmentList;
