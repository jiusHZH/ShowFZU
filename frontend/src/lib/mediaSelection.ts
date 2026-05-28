const MEGABYTE = 1024 * 1024

export const MAX_IMAGE_SIZE_BYTES = 10 * MEGABYTE
export const MAX_VIDEO_SIZE_BYTES = 50 * MEGABYTE
export const MAX_TOTAL_POST_MEDIA_BYTES = 200 * MEGABYTE

const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif'])
const IMAGE_MIME_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif'])
const VIDEO_EXTENSIONS = new Set(['.mp4', '.webm', '.ogg', '.mov'])
const VIDEO_MIME_TYPES = new Set(['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'])

interface ImagesSelection {
  files: File[]
  error: string | null
}

interface VideoSelection {
  file: File | null
  error: string | null
}

function getExtension(file: File) {
  const extensionIndex = file.name.lastIndexOf('.')
  return extensionIndex >= 0 ? file.name.slice(extensionIndex).toLowerCase() : ''
}

function matchesAcceptedType(file: File, extensions: Set<string>, mimeTypes: Set<string>) {
  return extensions.has(getExtension(file)) && (!file.type || mimeTypes.has(file.type.toLowerCase()))
}

function mediaTotalBytes(images: File[], video: File | null, retainedBytes: number) {
  return retainedBytes + images.reduce((total, file) => total + file.size, 0) + (video?.size ?? 0)
}

export function addPostImages(
  current: File[],
  selected: File[],
  video: File | null,
  retainedBytes = 0,
): ImagesSelection {
  const files = [...current]
  const messages: string[] = []

  selected.forEach((file) => {
    if (!matchesAcceptedType(file, IMAGE_EXTENSIONS, IMAGE_MIME_TYPES)) {
      messages.push(`${file.name} was not added. Use PNG, JPG, JPEG, or GIF images only.`)
      return
    }
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      messages.push(`${file.name} was not added because it exceeds the 10 MB image limit.`)
      return
    }
    if (mediaTotalBytes([...files, file], video, retainedBytes) > MAX_TOTAL_POST_MEDIA_BYTES) {
      messages.push(`${file.name} was not added because selected media would exceed the 200 MB post limit.`)
      return
    }
    files.push(file)
  })

  return { files, error: messages.length ? messages.join(' ') : null }
}

export function choosePostVideo(images: File[], selected: File | null, retainedBytes = 0): VideoSelection {
  if (!selected) {
    return { file: null, error: null }
  }
  if (!matchesAcceptedType(selected, VIDEO_EXTENSIONS, VIDEO_MIME_TYPES)) {
    return { file: null, error: `${selected.name} was not added. Use MP4, WEBM, OGG, or MOV video only.` }
  }
  if (selected.size > MAX_VIDEO_SIZE_BYTES) {
    return { file: null, error: `${selected.name} was not added because it exceeds the 50 MB video limit.` }
  }
  if (mediaTotalBytes(images, selected, retainedBytes) > MAX_TOTAL_POST_MEDIA_BYTES) {
    return {
      file: null,
      error: `${selected.name} was not added because selected media would exceed the 200 MB post limit.`,
    }
  }
  return { file: selected, error: null }
}
