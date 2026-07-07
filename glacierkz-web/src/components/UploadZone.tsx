"use client";

/* eslint-disable @next/next/no-img-element -- local object URL previews are not compatible with next/image optimization. */

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export default function UploadZone({ onFileSelected, disabled }: UploadZoneProps) {
  const [preview, setPreview] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[]) => {
      const file = accepted[0];
      if (!file) return;
      setPreview(URL.createObjectURL(file));
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/tiff": [".tif", ".tiff"], "image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"] },
    maxFiles: 1,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors",
        isDragActive ? "border-blue-500 bg-blue-50" : "border-zinc-300 hover:border-zinc-400",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <input {...getInputProps()} />
      {preview ? (
        <div className="flex flex-col items-center gap-3">
          <img src={preview} alt="Preview" className="max-h-48 rounded-lg object-contain" />
          <p className="text-sm text-zinc-500">Click or drag to replace</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 text-zinc-500">
          {isDragActive ? (
            <ImageIcon className="h-10 w-10 text-blue-500" />
          ) : (
            <Upload className="h-10 w-10" />
          )}
          <p className="text-sm font-medium">
            {isDragActive ? "Drop image here" : "Drag & drop or click to upload"}
          </p>
          <p className="text-xs text-zinc-400">TIFF, PNG, or JPEG — max 200 MB</p>
        </div>
      )}
    </div>
  );
}
