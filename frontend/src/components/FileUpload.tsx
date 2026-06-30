import { useCallback, useRef, useState } from 'react'
import { X, Upload, FileText, Image, Music, File } from 'lucide-react'
import { uploadFile } from '@/lib/api'
import type { UploadedFile } from '@/types'

interface FileUploadProps {
  files: UploadedFile[]
  onFilesChange: (files: UploadedFile[]) => void
  disabled?: boolean
}

function getFileIcon(contentType: string) {
  if (contentType.startsWith('image/')) return <Image className="h-3.5 w-3.5" />
  if (contentType === 'application/pdf') return <FileText className="h-3.5 w-3.5" />
  if (contentType.startsWith('audio/')) return <Music className="h-3.5 w-3.5" />
  return <File className="h-3.5 w-3.5" />
}

function getFileEmoji(contentType: string) {
  if (contentType.startsWith('image/')) return '🖼️'
  if (contentType === 'application/pdf') return '📄'
  if (contentType.startsWith('audio/')) return '🎙️'
  return '📎'
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
}

export function FileUpload({ files, onFilesChange, disabled }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState<string[]>([])
  const [isDragging, setIsDragging] = useState(false)

  const handleFiles = useCallback(
    async (rawFiles: FileList | null) => {
      if (!rawFiles || disabled) return

      const fileList = Array.from(rawFiles)
      const newUploading = fileList.map((f) => f.name)
      setUploading((prev) => [...prev, ...newUploading])

      try {
        const uploaded = await Promise.all(
          fileList.map(async (f) => {
            try {
              const result = await uploadFile(f)
              return result
            } catch (err) {
              console.error(`Failed to upload ${f.name}:`, err)
              return null
            } finally {
              setUploading((prev) => prev.filter((n) => n !== f.name))
            }
          }),
        )
        const valid = uploaded.filter(Boolean) as UploadedFile[]
        if (valid.length > 0) {
          onFilesChange([...files, ...valid])
        }
      } catch (e) {
        console.error('Upload error:', e)
      }
    },
    [files, onFilesChange, disabled],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles],
  )

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const onDragLeave = () => setIsDragging(false)

  const removeFile = (fileId: string) => {
    onFilesChange(files.filter((f) => f.file_id !== fileId))
  }

  return (
    <div className="space-y-2">
      {/* Drop zone — only show when no files queued and not loading */}
      {files.length === 0 && uploading.length === 0 && (
        <div
          className={`drop-zone flex items-center gap-3 px-3 py-2 cursor-pointer transition-all ${isDragging ? 'active' : ''} ${disabled ? 'opacity-40 pointer-events-none' : ''}`}
          onClick={() => !disabled && inputRef.current?.click()}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
        >
          <Upload className={`h-4 w-4 shrink-0 transition-colors ${isDragging ? 'text-primary' : 'text-muted-foreground'}`} />
          <span className="text-xs text-muted-foreground">
            {isDragging
              ? 'Drop files here...'
              : 'Attach files — images, PDFs, audio (drag & drop or click)'}
          </span>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*,.pdf,audio/*"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
            disabled={disabled}
          />
        </div>
      )}

      {/* Add more button when files already attached */}
      {(files.length > 0 || uploading.length > 0) && (
        <div className="flex items-center gap-2 flex-wrap">
          {/* Uploading indicators */}
          {uploading.map((name) => (
            <div key={name} className="file-tag animate-shimmer opacity-80">
              <div className="h-3 w-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <span className="max-w-[120px] truncate text-muted-foreground">{name}</span>
            </div>
          ))}

          {/* Uploaded files */}
          {files.map((f) => (
            <div key={f.file_id} className="file-tag group/file">
              {getFileIcon(f.content_type)}
              <span className="max-w-[120px] truncate" title={f.filename}>
                {getFileEmoji(f.content_type)} {f.filename}
              </span>
              <span className="text-muted-foreground/60 text-[10px]">
                {formatSize(f.size_bytes)}
              </span>
              <button
                onClick={() => removeFile(f.file_id)}
                className="ml-0.5 opacity-0 group-hover/file:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                disabled={disabled}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}

          {/* Add more */}
          {!disabled && (
            <button
              onClick={() => inputRef.current?.click()}
              className="file-tag opacity-60 hover:opacity-100 transition-opacity cursor-pointer"
            >
              <Upload className="h-3 w-3" />
              <span>Add more</span>
              <input
                ref={inputRef}
                type="file"
                multiple
                accept="image/*,.pdf,audio/*"
                className="hidden"
                onChange={(e) => handleFiles(e.target.files)}
                disabled={disabled}
              />
            </button>
          )}
        </div>
      )}
    </div>
  )
}
