import { useState } from 'react'
import type { FormEvent } from 'react'

import { Avatar } from '@/components/Avatar'
import { formatDateTime } from '@/lib/format'
import type { CommentNode } from '@/types/api'

interface CommentThreadProps {
  comments: CommentNode[]
  currentUserId: string | undefined
  onDelete: (commentId: string) => Promise<void>
  onReply: (commentId: string, body: string) => Promise<void>
  onRequireLogin: () => void
  isAuthenticated: boolean
}

export function CommentThread({
  comments,
  currentUserId,
  onDelete,
  onReply,
  onRequireLogin,
  isAuthenticated,
}: CommentThreadProps) {
  const [replyingTo, setReplyingTo] = useState<string | null>(null)
  const [replyBody, setReplyBody] = useState('')

  const handleReplySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!replyingTo) return
    await onReply(replyingTo, replyBody)
    setReplyBody('')
    setReplyingTo(null)
  }

  const startReply = (commentId: string) => {
    if (!isAuthenticated) {
      onRequireLogin()
      return
    }
    setReplyingTo(commentId)
  }

  return (
    <div className="comment-thread">
      {comments.length === 0 ? <p className="empty-state">No comments yet. Be the first to add one.</p> : null}
      {comments.map((comment) => (
        <article key={comment.id} className="comment-card">
          <header className="comment-card__header">
            <div className="comment-card__author">
              <Avatar user={comment.author} size="sm" />
              <div>
                <strong>{comment.author.username}</strong>
                <time>{formatDateTime(comment.created_at)}</time>
              </div>
            </div>
            <div className="comment-card__actions">
              {!comment.is_deleted ? (
                <button type="button" onClick={() => startReply(comment.id)}>
                  Reply
                </button>
              ) : null}
              {currentUserId === comment.author.id && !comment.is_deleted ? (
                <button type="button" onClick={() => void onDelete(comment.id)}>
                  Delete
                </button>
              ) : null}
            </div>
          </header>
          <p className={comment.is_deleted ? 'comment-card__body is-deleted' : 'comment-card__body'}>
            {comment.body}
          </p>
          {replyingTo === comment.id ? (
            <form className="comment-card__reply-form" onSubmit={(event) => void handleReplySubmit(event)}>
              <textarea
                placeholder="Write a reply"
                value={replyBody}
                onChange={(event) => setReplyBody(event.target.value)}
              />
              <div className="comment-card__reply-actions">
                <button type="submit">Post reply</button>
                <button type="button" onClick={() => setReplyingTo(null)}>
                  Cancel
                </button>
              </div>
            </form>
          ) : null}
          {comment.replies.length > 0 ? (
            <div className="comment-card__replies">
              {comment.replies.map((reply) => (
                <article key={reply.id} className="comment-card comment-card--reply">
                  <header className="comment-card__header">
                    <div className="comment-card__author">
                      <Avatar user={reply.author} size="sm" />
                      <div>
                        <strong>{reply.author.username}</strong>
                        <time>{formatDateTime(reply.created_at)}</time>
                      </div>
                    </div>
                    {currentUserId === reply.author.id && !reply.is_deleted ? (
                      <button type="button" onClick={() => void onDelete(reply.id)}>
                        Delete
                      </button>
                    ) : null}
                  </header>
                  <p className={reply.is_deleted ? 'comment-card__body is-deleted' : 'comment-card__body'}>
                    {reply.body}
                  </p>
                </article>
              ))}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  )
}
