import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileText, Image, Music, File } from 'lucide-react'
import { cn, formatBytes } from '@/lib/utils'
import { uploadFile } from '@/lib/api'
import type { UploadedFile } from '@/types'

interface FileUploadProps {
  files: UploadedFile[]
  onFilesChange: (files: UploadedFile[]) => void
  disabled?: boolean
}

function getFileIcon(contentType: string) {
  if (contentType.startsWith('image/')) return Image
  if (contentType.startsWith('audio/')) return Music
  if (contentType.includes('pdf')) return FileText
  return File
}

export function FileUpload({ files, onFilesChange, disabled }: FileUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setError(null)
      setUploading(true)
      try {
        const uploaded = await Promise.all(acceptedFiles.map(uploadFile))
        onFilesChange([...files, ...uploaded])
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [files, onFilesChange],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: disabled || uploading,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
      'application/pdf': ['.pdf'],
      'audio/*': ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm'],
    },
  })

  const removeFile = (fileId: string) => {
    onFilesChange(files.filter((f) => f.file_id !== fileId))
  }

  return (
    <div className="space-y-2">
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors',
          isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50',
          (disabled || uploading) && 'opacity-50 cursor-not-allowed',
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">
          {uploading ? 'Uploading...' : isDragActive ? 'Drop files here' : 'Drag & drop or click to upload'}
        </p>
        <p className="text-xs text-muted-foreground mt-1">Images, PDFs, Audio</p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((file) => {
            const Icon = getFileIcon(file.content_type)
            return (
              <div
                key={file.file_id}
                className="flex items-center gap-2 bg-secondary rounded-md px-3 py-1.5 text-sm"
              >
                <Icon className="h-4 w-4" />
                <span className="truncate max-w-[150px]">{file.filename}</span>
                <span className="text-xs text-muted-foreground">{formatBytes(file.size_bytes)}</span>
                <button
                  onClick={() => removeFile(file.file_id)}
                  className="hover:text-destructive"
                  disabled={disabled}
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
