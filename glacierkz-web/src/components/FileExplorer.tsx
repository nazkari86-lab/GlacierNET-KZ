"use client";

import { useState, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  Folder,
  File,
  FileText,
  FileImage,
  FileArchive,
  FileCode,
  ChevronRight,
  Search,
  Grid,
  List,
  ArrowUp,
  MoreVertical,
  Download,
  Trash2,
  Eye,
  HardDrive,
} from "lucide-react";

interface FileItem {
  id: string;
  name: string;
  type: "file" | "folder";
  size?: number;
  modifiedAt?: string;
  mimeType?: string;
  children?: FileItem[];
  path: string;
}

interface FileExplorerProps {
  items: FileItem[];
  onNavigate?: (path: string) => void;
  onFileClick?: (file: FileItem) => void;
  onDownload?: (file: FileItem) => void;
  onDelete?: (ids: string[]) => void;
  selectedIds?: string[];
  onSelect?: (ids: string[]) => void;
  className?: string;
  showBreadcrumb?: boolean;
  storageUsed?: number;
  storageTotal?: number;
}

function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return "—";
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function getFileIcon(name: string, type: "file" | "folder") {
  if (type === "folder") return <Folder className="w-4 h-4 text-amber-500" />;
  const ext = name.split(".").pop()?.toLowerCase() || "";
  if (["jpg", "jpeg", "png", "gif", "webp", "tiff", "tif"].includes(ext))
    return <FileImage className="w-4 h-4 text-purple-500" />;
  if (["zip", "tar", "gz", "7z", "rar"].includes(ext))
    return <FileArchive className="w-4 h-4 text-yellow-600" />;
  if (["py", "js", "ts", "jsx", "tsx", "rs", "go"].includes(ext))
    return <FileCode className="w-4 h-4 text-green-600" />;
  if (["md", "txt", "csv", "json", "xml", "yml", "yaml"].includes(ext))
    return <FileText className="w-4 h-4 text-blue-500" />;
  if (["tif", "tiff", "shp", "geojson"].includes(ext))
    return <File className="w-4 h-4 text-teal-600" />;
  return <File className="w-4 h-4 text-gray-500" />;
}

export default function FileExplorer({
  items,
  onNavigate,
  onFileClick,
  onDownload,
  onDelete,
  selectedIds = [],
  onSelect,
  className,
  showBreadcrumb = true,
  storageUsed = 0,
  storageTotal = 10737418240,
}: FileExplorerProps) {
  const [currentPath, setCurrentPath] = useState("/");
  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
  const [searchQuery, setSearchQuery] = useState("");
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; item: FileItem } | null>(null);

  const currentItems = useMemo(() => {
    const pathParts = currentPath.split("/").filter(Boolean);
    let current = items;
    for (const part of pathParts) {
      const folder = current.find((i) => i.name === part && i.type === "folder");
      if (folder?.children) current = folder.children;
      else return [];
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return current.filter((item) => item.name.toLowerCase().includes(q));
    }
    return current;
  }, [items, currentPath, searchQuery]);

  const breadcrumbs = useMemo(() => {
    const parts = currentPath.split("/").filter(Boolean);
    return [{ name: "Root", path: "/" }, ...parts.map((p, i) => ({ name: p, path: `/${parts.slice(0, i + 1).join("/")}` }))];
  }, [currentPath]);

  const navigateTo = useCallback(
    (path: string) => {
      setCurrentPath(path);
      onNavigate?.(path);
    },
    [onNavigate]
  );

  const handleItemClick = useCallback(
    (item: FileItem) => {
      if (item.type === "folder") {
        navigateTo(item.path);
      } else {
        onFileClick?.(item);
      }
    },
    [navigateTo, onFileClick]
  );

  const handleCheckboxChange = useCallback(
    (itemId: string) => {
      const next = selectedIds.includes(itemId)
        ? selectedIds.filter((id) => id !== itemId)
        : [...selectedIds, itemId];
      onSelect?.(next);
    },
    [selectedIds, onSelect]
  );

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, item: FileItem) => {
      e.preventDefault();
      setContextMenu({ x: e.clientX, y: e.clientY, item });
    },
    []
  );

  const storagePercent = Math.min((storageUsed / storageTotal) * 100, 100);

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 overflow-hidden", className)}>
      <div className="flex items-center justify-between p-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-gray-500" />
          <div>
            <div className="text-xs font-medium text-gray-700">Storage</div>
            <div className="text-[10px] text-gray-400">
              {formatFileSize(storageUsed)} of {formatFileSize(storageTotal)}
            </div>
          </div>
          <div className="w-24 h-1.5 bg-gray-200 rounded-full ml-2">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                storagePercent > 90 ? "bg-red-500" : storagePercent > 70 ? "bg-amber-500" : "bg-blue-500"
              )}
              style={{ width: `${storagePercent}%` }}
            />
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter files..."
              className="pl-7 pr-2 py-1 text-xs border border-gray-200 rounded-md w-40 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={() => setViewMode("list")}
            className={cn("p-1.5 rounded", viewMode === "list" ? "bg-gray-100" : "hover:bg-gray-50")}
          >
            <List className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewMode("grid")}
            className={cn("p-1.5 rounded", viewMode === "grid" ? "bg-gray-100" : "hover:bg-gray-50")}
          >
            <Grid className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {showBreadcrumb && (
        <div className="flex items-center gap-1 px-3 py-2 border-b border-gray-50 text-xs">
          {breadcrumbs.map((crumb, i) => (
            <div key={crumb.path} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="w-3 h-3 text-gray-300" />}
              <button
                onClick={() => navigateTo(crumb.path)}
                className={cn(
                  "hover:text-blue-600 truncate max-w-[120px]",
                  i === breadcrumbs.length - 1 ? "text-gray-900 font-medium" : "text-gray-500"
                )}
              >
                {crumb.name}
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="overflow-y-auto max-h-[500px]">
        {currentPath !== "/" && (
          <button
            onClick={() => {
              const parts = currentPath.split("/").filter(Boolean);
              parts.pop();
              navigateTo(`/${parts.join("/")}`);
            }}
            className="flex items-center gap-2 w-full px-3 py-2 text-xs text-gray-500 hover:bg-gray-50 border-b border-gray-50"
          >
            <ArrowUp className="w-3.5 h-3.5" />
            <span>Go up</span>
          </button>
        )}

        {currentItems.length === 0 ? (
          <div className="px-3 py-12 text-center text-sm text-gray-500">
            {searchQuery ? "No matching files" : "Empty folder"}
          </div>
        ) : viewMode === "list" ? (
          <div>
            {currentItems
              .sort((a, b) => {
                if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
                return a.name.localeCompare(b.name);
              })
              .map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 text-xs hover:bg-gray-50 border-b border-gray-50 cursor-pointer group",
                    selectedIds.includes(item.id) && "bg-blue-50"
                  )}
                  onClick={() => handleItemClick(item)}
                  onContextMenu={(e) => handleContextMenu(e, item)}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(item.id)}
                    onChange={() => handleCheckboxChange(item.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="rounded border-gray-300"
                  />
                  {getFileIcon(item.name, item.type)}
                  <span className="flex-1 truncate text-gray-700">{item.name}</span>
                  {item.size !== undefined && (
                    <span className="text-gray-400 w-20 text-right">{formatFileSize(item.size)}</span>
                  )}
                  {item.modifiedAt && (
                    <span className="text-gray-400 w-32">{new Date(item.modifiedAt).toLocaleDateString()}</span>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setContextMenu({ x: e.clientX, y: e.clientY, item });
                    }}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-200"
                  >
                    <MoreVertical className="w-3 h-3" />
                  </button>
                </div>
              ))}
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-2 p-3">
            {currentItems.map((item) => (
              <div
                key={item.id}
                className={cn(
                  "flex flex-col items-center gap-1.5 p-3 rounded-lg hover:bg-gray-50 cursor-pointer border border-transparent",
                  selectedIds.includes(item.id) && "bg-blue-50 border-blue-200"
                )}
                onClick={() => handleItemClick(item)}
                onContextMenu={(e) => handleContextMenu(e, item)}
              >
                <div className="scale-150">{getFileIcon(item.name, item.type)}</div>
                <span className="text-[11px] text-gray-700 text-center truncate w-full">{item.name}</span>
                {item.size !== undefined && (
                  <span className="text-[10px] text-gray-400">{formatFileSize(item.size)}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {selectedIds.length > 0 && (
        <div className="flex items-center justify-between px-3 py-2 border-t border-gray-100 bg-gray-50 text-xs">
          <span className="text-gray-500">{selectedIds.length} items selected</span>
          <div className="flex items-center gap-1.5">
            {onDownload && (
              <button className="flex items-center gap-1 px-2 py-1 bg-white border border-gray-200 rounded hover:bg-gray-50">
                <Download className="w-3 h-3" /> Download
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => onDelete(selectedIds)}
                className="flex items-center gap-1 px-2 py-1 bg-white border border-red-200 text-red-600 rounded hover:bg-red-50"
              >
                <Trash2 className="w-3 h-3" /> Delete
              </button>
            )}
          </div>
        </div>
      )}

      {contextMenu && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setContextMenu(null)} />
          <div
            className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 w-40"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            {contextMenu.item.type === "file" && (
              <button
                onClick={() => {
                  onFileClick?.(contextMenu.item);
                  setContextMenu(null);
                }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-gray-50"
              >
                <Eye className="w-3 h-3" /> View
              </button>
            )}
            {onDownload && contextMenu.item.type === "file" && (
              <button
                onClick={() => {
                  onDownload(contextMenu.item);
                  setContextMenu(null);
                }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-gray-50"
              >
                <Download className="w-3 h-3" /> Download
              </button>
            )}
            {onDelete && (
              <button
                onClick={() => {
                  onDelete([contextMenu.item.id]);
                  setContextMenu(null);
                }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-red-600 hover:bg-red-50"
              >
                <Trash2 className="w-3 h-3" /> Delete
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export type { FileExplorerProps, FileItem };
