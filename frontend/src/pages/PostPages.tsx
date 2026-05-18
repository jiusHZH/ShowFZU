import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { Avatar } from '@/components/Avatar'
import { CommentThread } from '@/components/CommentThread'
import { MediaCarousel } from '@/components/MediaCarousel'
import { categoryList } from '@/data/categories'
import { useAuth } from '@/context/useAuth'
import {
  createComment,
  createPost,
  createReply,
  deleteComment,
  deletePost,
  favoritePost,
  getComments,
  getPost,
  likePost,
  unfavoritePost,
  unlikePost,
  updatePost,
} from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import type { CommentNode, PostCategory, PostDetail } from '@/types/api'

function fileListToArray(fileList: FileList | null) {
  return fileList ? Array.from(fileList) : []
}

function buildCreatePayload(input: {
  title: string
  category: PostCategory
  body: string
  images: File[]
  video: File | null
}) {
  const formData = new FormData()
  formData.append('title', input.title)
  formData.append('category', input.category)
  formData.append('body', input.body)
  input.images.forEach((image) => formData.append('images', image))
  if (input.video) {
    formData.append('video', input.video)
  }
  return formData
}

function buildEditPayload(input: {
  title: string
  category: PostCategory
  body: string
  keptImageIds: string[]
  removeVideo: boolean
  images: File[]
  video: File | null
}) {
  const formData = new FormData()
  formData.append('title', input.title)
  formData.append('category', input.category)
  formData.append('body', input.body)
  formData.append('existing_image_ids', JSON.stringify(input.keptImageIds))
  formData.append('remove_video', String(input.removeVideo))
  input.images.forEach((image) => formData.append('images', image))
  if (input.video) {
    formData.append('video', input.video)
  }
  return formData
}

function useProtectedAction() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated } = useAuth()

  return () => {
    if (isAuthenticated) return true
    navigate(`/login?returnTo=${encodeURIComponent(`${location.pathname}${location.search}`)}`)
    return false
  }
}

export function CreatePostPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState<PostCategory>('Campus Landmark')
  const [body, setBody] = useState('')
  const [images, setImages] = useState<File[]>([])
  const [video, setVideo] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      const response = await createPost(
        buildCreatePayload({
          title,
          category,
          body,
          images,
          video,
        }),
      )
      navigate(`/posts/${response.id}`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not create post.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="editor-layout">
      <header className="page-intro">
        <span className="eyebrow">Create post</span>
        <h1>Publish directly to the public campus feed.</h1>
        <p>Title and category are required. Then add body text, images, or one video. No drafts, no moderation queue.</p>
      </header>
      <form className="editor-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="field">
          <span>Title</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label className="field">
          <span>Category</span>
          <select value={category} onChange={(event) => setCategory(event.target.value as PostCategory)}>
            {categoryList.map((item) => (
              <option key={item.slug} value={item.name}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Body</span>
          <textarea
            rows={8}
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder="Write about the campus atmosphere, study experience, or place you want to share."
          />
        </label>
        <label className="field">
          <span>Images</span>
          <input
            accept=".png,.jpg,.jpeg,.gif"
            multiple
            type="file"
            onChange={(event) => setImages(fileListToArray(event.target.files))}
          />
          {images.length > 0 ? <small>{images.length} image file(s) selected.</small> : null}
        </label>
        <label className="field">
          <span>Video</span>
          <input
            accept=".mp4,.webm,.ogg,.mov"
            type="file"
            onChange={(event) => setVideo(event.target.files?.[0] ?? null)}
          />
          {video ? <small>{video.name}</small> : null}
        </label>
        {error ? <p className="error-banner">{error}</p> : null}
        <div className="button-row">
          <button className="button button--primary" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Publishing…' : 'Publish post'}
          </button>
        </div>
      </form>
    </div>
  )
}

export function EditPostPage() {
  const navigate = useNavigate()
  const { postId } = useParams()
  const [post, setPost] = useState<PostDetail | null>(null)
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState<PostCategory>('Campus Landmark')
  const [body, setBody] = useState('')
  const [keptImageIds, setKeptImageIds] = useState<string[]>([])
  const [removeVideo, setRemoveVideo] = useState(false)
  const [images, setImages] = useState<File[]>([])
  const [video, setVideo] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!postId) return
    let cancelled = false
    const loadPost = async () => {
      try {
        const payload = await getPost(postId)
        if (!cancelled) {
          setPost(payload)
          setTitle(payload.title)
          setCategory(payload.category)
          setBody(payload.body ?? '')
          setKeptImageIds(payload.media.filter((item) => item.type === 'image').map((item) => item.id))
          setRemoveVideo(false)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load post.')
        }
      }
    }
    void loadPost()
    return () => {
      cancelled = true
    }
  }, [postId])

  const existingImages = useMemo(() => post?.media.filter((item) => item.type === 'image') ?? [], [post])
  const existingVideo = useMemo(() => post?.media.find((item) => item.type === 'video') ?? null, [post])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!postId) return
    setError(null)
    try {
      const payload = await updatePost(
        postId,
        buildEditPayload({
          title,
          category,
          body,
          keptImageIds,
          removeVideo,
          images,
          video,
        }),
      )
      navigate(`/posts/${payload.id}`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not update the post.')
    }
  }

  if (!post) {
    return <p>{error ?? 'Loading post editor…'}</p>
  }

  return (
    <div className="editor-layout">
      <header className="page-intro">
        <span className="eyebrow">Edit post</span>
        <h1>Adjust text, category, and media without changing the post URL.</h1>
      </header>
      <form className="editor-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="field">
          <span>Title</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label className="field">
          <span>Category</span>
          <select value={category} onChange={(event) => setCategory(event.target.value as PostCategory)}>
            {categoryList.map((item) => (
              <option key={item.slug} value={item.name}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Body</span>
          <textarea rows={8} value={body} onChange={(event) => setBody(event.target.value)} />
        </label>
        {existingImages.length > 0 ? (
          <fieldset className="field-set">
            <legend>Existing images</legend>
            <div className="existing-media-grid">
              {existingImages.map((image) => {
                const checked = keptImageIds.includes(image.id)
                return (
                  <label key={image.id} className="existing-media-card">
                    <img src={image.url} alt="" />
                    <span>
                      <input
                        checked={checked}
                        type="checkbox"
                        onChange={(event) =>
                          setKeptImageIds((current) =>
                            event.target.checked
                              ? [...current, image.id]
                              : current.filter((id) => id !== image.id),
                          )
                        }
                      />
                      Keep this image
                    </span>
                  </label>
                )
              })}
            </div>
          </fieldset>
        ) : null}
        {existingVideo ? (
          <label className="field checkbox-field">
            <input
              checked={removeVideo}
              type="checkbox"
              onChange={(event) => setRemoveVideo(event.target.checked)}
            />
            <span>Remove current video</span>
          </label>
        ) : null}
        <label className="field">
          <span>Add images</span>
          <input
            accept=".png,.jpg,.jpeg,.gif"
            multiple
            type="file"
            onChange={(event) => setImages(fileListToArray(event.target.files))}
          />
        </label>
        <label className="field">
          <span>Replace video</span>
          <input
            accept=".mp4,.webm,.ogg,.mov"
            type="file"
            onChange={(event) => setVideo(event.target.files?.[0] ?? null)}
          />
        </label>
        {error ? <p className="error-banner">{error}</p> : null}
        <div className="button-row">
          <button className="button button--primary" type="submit">
            Save changes
          </button>
        </div>
      </form>
    </div>
  )
}

export function PostDetailPage() {
  const { postId } = useParams()
  const { user, isAuthenticated } = useAuth()
  const requireLogin = useProtectedAction()
  const navigate = useNavigate()
  const [post, setPost] = useState<PostDetail | null>(null)
  const [comments, setComments] = useState<CommentNode[]>([])
  const [error, setError] = useState<string | null>(null)
  const [commentBody, setCommentBody] = useState('')
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)

  useEffect(() => {
    if (!postId) return
    let cancelled = false
    const load = async () => {
      setError(null)
      try {
        const [postPayload, commentsPayload] = await Promise.all([getPost(postId), getComments(postId)])
        if (!cancelled) {
          setPost(postPayload)
          setComments(commentsPayload.items)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load post.')
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [postId])

  const refreshComments = async () => {
    if (!postId) return
    const commentsPayload = await getComments(postId)
    setComments(commentsPayload.items)
    const updatedPost = await getPost(postId)
    setPost(updatedPost)
  }

  const toggleLike = async () => {
    if (!post || !requireLogin()) return
    const response = post.is_liked ? await unlikePost(post.id) : await likePost(post.id)
    setPost({
      ...post,
      is_liked: response.active,
      like_count: response.count,
    })
  }

  const toggleFavorite = async () => {
    if (!post || !requireLogin()) return
    const response = post.is_favorited ? await unfavoritePost(post.id) : await favoritePost(post.id)
    setPost({
      ...post,
      is_favorited: response.active,
      favorite_count: response.count,
    })
  }

  const handleCommentSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!post || !requireLogin()) return
    setIsSubmittingComment(true)
    try {
      const response = await createComment(post.id, commentBody)
      setComments(response.items)
      setCommentBody('')
      const updatedPost = await getPost(post.id)
      setPost(updatedPost)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not create comment.')
    } finally {
      setIsSubmittingComment(false)
    }
  }

  const handleReply = async (commentId: string, body: string) => {
    if (!requireLogin()) return
    const response = await createReply(commentId, body)
    setComments(response.items)
    await refreshComments()
  }

  const handleDeleteComment = async (commentId: string) => {
    await deleteComment(commentId)
    await refreshComments()
  }

  const handleDeletePost = async () => {
    if (!post) return
    if (!window.confirm('Delete this post permanently?')) return
    await deletePost(post.id)
    navigate('/profile/posts')
  }

  if (error && !post) {
    return <p className="error-banner">{error}</p>
  }

  if (!post) {
    return <p>Loading post…</p>
  }

  return (
    <div className="stack-lg">
      <article className="post-detail">
        <div className="post-detail__header">
          <div className="stack-sm">
            <div className="post-detail__meta">
              <Link to={`/categories/${categoryList.find((item) => item.name === post.category)?.slug ?? ''}`}>
                {post.category}
              </Link>
              <span>{formatDateTime(post.published_at)}</span>
            </div>
            <h1>{post.title}</h1>
            <div className="post-detail__author">
              <Link className="post-detail__author-link" to={`/users/${post.author.id}`}>
                <Avatar user={post.author} size="md" />
                <span>
                  <strong>{post.author.username}</strong>
                  <small>{post.author.bio || 'Public author page available.'}</small>
                </span>
              </Link>
            </div>
          </div>
          {post.can_edit ? (
            <div className="button-row">
              <Link className="button button--ghost" to={`/posts/${post.id}/edit`}>
                Edit
              </Link>
              <button className="button button--ghost" onClick={() => void handleDeletePost()} type="button">
                Delete
              </button>
            </div>
          ) : null}
        </div>
        <MediaCarousel media={post.media} />
        {post.body ? <div className="post-detail__body"><p>{post.body}</p></div> : null}
        <div className="post-detail__actions">
          <button className="button button--ghost" onClick={() => void toggleLike()} type="button">
            {post.is_liked ? 'Unlike' : 'Like'} ({post.like_count})
          </button>
          <button className="button button--ghost" onClick={() => void toggleFavorite()} type="button">
            {post.is_favorited ? 'Unfavorite' : 'Favorite'} ({post.favorite_count})
          </button>
          <span>{post.comment_count} comments</span>
        </div>
      </article>

      <section className="stack-md">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Comments</span>
            <h2>Two levels only: main comments and one layer of replies.</h2>
          </div>
        </div>
        <form className="comment-composer" onSubmit={(event) => void handleCommentSubmit(event)}>
          <textarea
            rows={4}
            placeholder={isAuthenticated ? 'Add a comment' : 'Sign in to comment'}
            value={commentBody}
            onChange={(event) => setCommentBody(event.target.value)}
            onFocus={() => {
              if (!isAuthenticated) {
                requireLogin()
              }
            }}
          />
          <div className="button-row">
            <button className="button button--primary" disabled={isSubmittingComment} type="submit">
              {isSubmittingComment ? 'Posting…' : 'Post comment'}
            </button>
          </div>
        </form>
        <CommentThread
          comments={comments}
          currentUserId={user?.id}
          isAuthenticated={isAuthenticated}
          onDelete={handleDeleteComment}
          onReply={handleReply}
          onRequireLogin={() => {
            requireLogin()
          }}
        />
      </section>
    </div>
  )
}
