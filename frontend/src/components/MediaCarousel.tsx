import { useState } from 'react'

import { fileSizeLabel } from '@/lib/format'
import type { PostMediaItem } from '@/types/api'

interface MediaCarouselProps {
  media: PostMediaItem[]
}

export function MediaCarousel({ media }: MediaCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0)

  if (media.length === 0) {
    return <img className="media-carousel__fallback" src="/default-cover.svg" alt="Default cover" />
  }

  const activeItem = media[activeIndex]

  return (
    <div className="media-carousel">
      <div className="media-carousel__viewer">
        {activeItem.type === 'video' ? (
          <video controls playsInline poster={activeItem.thumbnail_url ?? undefined}>
            <source src={activeItem.url} type={activeItem.mime_type} />
          </video>
        ) : (
          <img src={activeItem.url} alt="" loading="lazy" />
        )}
      </div>
      <div className="media-carousel__toolbar">
        <span>
          {activeIndex + 1} / {media.length}
        </span>
        <span>{fileSizeLabel(activeItem.size_bytes)}</span>
      </div>
      {media.length > 1 ? (
        <div className="media-carousel__thumbs">
          {media.map((item, index) => (
            <button
              key={item.id}
              className={index === activeIndex ? 'media-carousel__thumb is-active' : 'media-carousel__thumb'}
              type="button"
              onClick={() => setActiveIndex(index)}
            >
              <img src={item.thumbnail_url ?? item.url} alt="" />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

