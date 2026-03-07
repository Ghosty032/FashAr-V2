"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import imageCompression from "browser-image-compression";
import { Upload, X, ImageIcon, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface ImageUploadZoneProps {
  onImageReady: (file: File, previewUrl: string) => void;
  onClear: () => void;
  previewUrl: string | null;
}

export default function ImageUploadZone({ onImageReady, onClear, previewUrl }: ImageUploadZoneProps) {
  const [isCompressing, setIsCompressing] = useState(false);

  const processFile = useCallback(async (file: File) => {
    // Validate type
    const validTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!validTypes.includes(file.type)) {
      toast.error("Unsupported format. Please use JPEG, PNG, or WebP.");
      return;
    }

    setIsCompressing(true);
    try {
      // Compress to max 2MB
      const compressed = await imageCompression(file, {
        maxSizeMB: 2,
        maxWidthOrHeight: 1920,
        useWebWorker: true,
      });

      const url = URL.createObjectURL(compressed);
      onImageReady(compressed, url);
      toast.success(`Compressed: ${(file.size / 1024 / 1024).toFixed(1)}MB → ${(compressed.size / 1024 / 1024).toFixed(1)}MB`);
    } catch {
      toast.error("Failed to process image. Please try another photo.");
    } finally {
      setIsCompressing(false);
    }
  }, [onImageReady]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => {
      if (accepted.length > 0) processFile(accepted[0]);
    },
    accept: { "image/jpeg": [], "image/png": [], "image/webp": [] },
    maxFiles: 1,
    disabled: isCompressing,
  });

  if (previewUrl) {
    return (
      <div className="relative rounded-2xl overflow-hidden border border-gray-200 bg-gray-50 group">
        <img src={previewUrl} alt="Outfit preview" className="w-full h-80 object-contain bg-gray-100" />
        <button
          onClick={(e) => { e.stopPropagation(); onClear(); }}
          className="absolute top-3 right-3 bg-black/70 hover:bg-black text-white rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <X className="w-4 h-4" />
        </button>
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-4">
          <p className="text-white text-sm font-medium">Photo ready for analysis</p>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`relative rounded-2xl border-2 border-dashed p-10 text-center cursor-pointer transition-all duration-200
        ${isDragActive ? "border-black bg-gray-100 scale-[1.01]" : "border-gray-300 hover:border-gray-400 bg-white"}
        ${isCompressing ? "pointer-events-none opacity-60" : ""}`}
    >
      <input {...getInputProps()} />
      {isCompressing ? (
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-10 h-10 text-gray-400 animate-spin" />
          <p className="text-sm text-gray-500">Compressing image…</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          {isDragActive ? (
            <ImageIcon className="w-12 h-12 text-black" />
          ) : (
            <Upload className="w-10 h-10 text-gray-400" />
          )}
          <div>
            <p className="text-sm font-medium text-gray-700">
              {isDragActive ? "Drop your outfit photo here" : "Drag & drop your outfit photo"}
            </p>
            <p className="text-xs text-gray-400 mt-1">JPEG, PNG, or WebP · Auto-compressed to 2MB</p>
          </div>
        </div>
      )}
    </div>
  );
}
