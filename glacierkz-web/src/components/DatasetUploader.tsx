'use client';

import React, { useState, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';

interface UploadFile {
  id: string;
  file: File;
  name: string;
  size: number;
  progress: number;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
}

interface DatasetUploaderProps {
  onUpload: (files: File[]) => void;
  maxFiles?: number;
  acceptedTypes?: string[];
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

const STATUS_ICON: Record<UploadFile['status'], string> = {
  pending: '○',
  uploading: '↻',
  done: '✓',
  error: '✕',
};

const STATUS_COLOR: Record<UploadFile['status'], string> = {
  pending: 'text-zinc-400',
  uploading: 'text-blue-500',
  done: 'text-emerald-500',
  error: 'text-red-500',
};

export default function DatasetUploader({
  onUpload,
  maxFiles = 10,
  acceptedTypes = ['.tif', '.tiff', '.npy', '.png', '.jpg', '.jpeg'],
}: DatasetUploaderProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): string | null => {
      const ext = `.${file.name.split('.').pop()?.toLowerCase()}`;
      if (!acceptedTypes.includes(ext)) {
        return `Unsupported file type: ${ext}`;
      }
      if (file.size > 500 * 1024 * 1024) {
        return 'File exceeds 500 MB limit';
      }
      return null;
    },
    [acceptedTypes]
  );

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const arr = Array.from(incoming);
      setFiles((prev) => {
        const remaining = maxFiles - prev.length;
        const toAdd = arr.slice(0, remaining);
        return [
          ...prev,
          ...toAdd.map((file) => {
            const err = validateFile(file);
            return {
              id: `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              file,
              name: file.name,
              size: file.size,
              progress: 0,
              status: err ? ('error' as const) : ('pending' as const),
              error: err ?? undefined,
            };
          }),
        ];
      });
    },
    [maxFiles, validateFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles]
  );

  const handleBrowse = () => inputRef.current?.click();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(e.target.files);
    e.target.value = '';
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleUploadAll = () => {
    const validFiles = files.filter((f) => f.status === 'pending').map((f) => f.file);
    if (validFiles.length === 0) return;

    setFiles((prev) =>
      prev.map((f) => (f.status === 'pending' ? { ...f, status: 'uploading' as const, progress: 30 } : f))
    );

    setTimeout(() => {
      setFiles((prev) =>
        prev.map((f) => (f.status === 'uploading' ? { ...f, status: 'done' as const, progress: 100 } : f))
      );
      onUpload(validFiles);
    }, 1200);
  };

  const pendingCount = files.filter((f) => f.status === 'pending').length;

  return (
    <div className="space-y-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleBrowse}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleBrowse(); } }}
        aria-label="Upload dataset files"
        className={cn(
          'relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors',
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-zinc-300 hover:border-zinc-400',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleInputChange}
          className="sr-only"
          aria-hidden="true"
        />
        <svg
          className={cn('h-10 w-10 mb-3', isDragging ? 'text-blue-500' : 'text-zinc-400')}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
        <p className="text-sm font-medium text-zinc-700">
          {isDragging ? 'Drop files here' : 'Drag & drop files or click to browse'}
        </p>
        <p className="mt-1 text-xs text-zinc-400">
          {acceptedTypes.join(', ')} — max {maxFiles} files
        </p>
      </div>

      {files.length > 0 && (
        <ul className="space-y-1.5" aria-label="Uploaded files">
          {files.map((f) => (
            <li
              key={f.id}
              className="flex items-center gap-3 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            >
              <span className={cn('text-base font-bold', STATUS_COLOR[f.status])} aria-hidden="true">
                {STATUS_ICON[f.status]}
              </span>
              <div className="flex-1 min-w-0">
                <div className="truncate font-medium text-zinc-800">{f.name}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-zinc-400">{formatBytes(f.size)}</span>
                  {f.status === 'uploading' && (
                    <div className="h-1.5 flex-1 max-w-[120px] rounded-full bg-zinc-100">
                      <div
                        className="h-full rounded-full bg-blue-500 transition-all"
                        style={{ width: `${f.progress}%` }}
                      />
                    </div>
                  )}
                  {f.error && <span className="text-xs text-red-500">{f.error}</span>}
                </div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(f.id); }}
                className="shrink-0 rounded p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 transition-colors"
                aria-label={`Remove ${f.name}`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}

      {pendingCount > 0 && (
        <button
          onClick={handleUploadAll}
          className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          aria-label={`Upload ${pendingCount} files`}
        >
          Upload {pendingCount} file{pendingCount !== 1 ? 's' : ''}
        </button>
      )}
    </div>
  );
}
