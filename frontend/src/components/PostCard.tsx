import { Link } from 'react-router-dom'

import { Avatar } from '@/components/Avatar'
import { getSlugForCategory } from '@/data/categories'
import { formatDate } from '@/lib/format'
import type { PostSummary } from '@/types/api'

interface PostCardProps {
  post: PostSummary
}

export function PostCard({ post }: PostCardProps) {
  return (
    <article className="post-card">
      <Link className="post-card__media" to={`/posts/${post.id}`}>
        <img
          className="post-card__cover"
          src={post.cover_url ?? '/default-cover.svg'}
          alt={post.title}
        />
        <div className="post-card__badges">
          {post.has_video ? <span>Video</span> : null}
          {post.image_count > 1 ? <span>{post.image_count} Images</span> : null}
          <span>{post.category}</span>
        </div>
      </Link>
      <div className="post-card__content">
        <div className="post-card__meta">
          <Link to={`/categories/${getSlugForCategory(post.category)}`}>{post.category}</Link>
          <span>{formatDate(post.published_at)}</span>
        </div>
        <Link className="post-card__title" to={`/posts/${post.id}`}>
          <h3>{post.title}</h3>
        </Link>
        {post.body_excerpt ? <p className="post-card__excerpt">{post.body_excerpt}</p> : null}
        <div className="post-card__footer">
          <Link className="post-card__author" to={`/users/${post.author.id}`}>
            <Avatar user={post.author} size="sm" />
            <span>{post.author.username}</span>
          </Link>
          <div className="post-card__stats">
            <span>♥ {post.like_count}</span>
            <span>☆ {post.favorite_count}</span>
          </div>
        </div>
      </div>
    </article>
  )
}

