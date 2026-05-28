import type {
  AuthResponse,
  CommentsResponse,
  ForgotPasswordStartResponse,
  InteractionState,
  LoginMethod,
  MessageResponse,
  PaginatedPosts,
  PostDetail,
  PostSummary,
  PrivateProfile,
  PublicAuthorProfile,
  SessionStateResponse,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function getInfrastructureErrorMessage(status: number, hasApiMessage: boolean) {
  if (status === 502 || status === 504 || (status === 503 && !hasApiMessage)) {
    return 'ShowFZU could not reach the server. Please try again in a moment.'
  }
  if (status >= 500 && !(status === 503 && hasApiMessage)) {
    return 'ShowFZU hit a server error. Please try again in a moment.'
  }
  return null
}

function getApiErrorMessage(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) {
    return fallback
  }

  const detail = payload.detail
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const validationError = detail.find(
      (item): item is { msg: string } =>
        Boolean(item) && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string',
    )
    if (validationError) {
      return validationError.msg.replace(/^Value error,\s*/u, '')
    }
  }

  return fallback
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  const isFormData = init?.body instanceof FormData
  if (!isFormData && init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      ...init,
      headers,
    })
  } catch {
    throw new ApiError(0, 'ShowFZU could not reach the server. Please try again in a moment.')
  }

  const contentType = response.headers.get('content-type') ?? ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const apiMessage = getApiErrorMessage(payload, '')
    const infrastructureMessage = getInfrastructureErrorMessage(response.status, Boolean(apiMessage))
    const message = infrastructureMessage ?? (apiMessage || response.statusText || 'Request failed')
    throw new ApiError(response.status, message)
  }

  return payload as T
}

export function listPosts(params?: { q?: string; category?: string; page?: number; pageSize?: number }) {
  const search = new URLSearchParams()
  if (params?.q) search.set('q', params.q)
  if (params?.category) search.set('category', params.category)
  if (params?.page) search.set('page', String(params.page))
  if (params?.pageSize) search.set('page_size', String(params.pageSize))
  const query = search.toString()
  return apiFetch<PaginatedPosts>(`/posts${query ? `?${query}` : ''}`)
}

export function getPost(postId: string) {
  return apiFetch<PostDetail>(`/posts/${postId}`)
}

export function createPost(formData: FormData) {
  return apiFetch<PostDetail>('/posts', {
    method: 'POST',
    body: formData,
  })
}

export function updatePost(postId: string, formData: FormData) {
  return apiFetch<PostDetail>(`/posts/${postId}`, {
    method: 'PATCH',
    body: formData,
  })
}

export function deletePost(postId: string) {
  return apiFetch<MessageResponse>(`/posts/${postId}`, { method: 'DELETE' })
}

export function likePost(postId: string) {
  return apiFetch<InteractionState>(`/posts/${postId}/like`, { method: 'POST' })
}

export function unlikePost(postId: string) {
  return apiFetch<InteractionState>(`/posts/${postId}/like`, { method: 'DELETE' })
}

export function favoritePost(postId: string) {
  return apiFetch<InteractionState>(`/posts/${postId}/favorite`, { method: 'POST' })
}

export function unfavoritePost(postId: string) {
  return apiFetch<InteractionState>(`/posts/${postId}/favorite`, { method: 'DELETE' })
}

export function getComments(postId: string) {
  return apiFetch<CommentsResponse>(`/posts/${postId}/comments`)
}

export function createComment(postId: string, body: string) {
  return apiFetch<CommentsResponse>(`/posts/${postId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  })
}

export function createReply(commentId: string, body: string) {
  return apiFetch<CommentsResponse>(`/comments/${commentId}/replies`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  })
}

export function deleteComment(commentId: string) {
  return apiFetch<MessageResponse>(`/comments/${commentId}`, { method: 'DELETE' })
}

export function register(payload: {
  account_id: string
  username: string
  password: string
  confirm_password: string
  security_question: string
  security_answer: string
}) {
  return apiFetch<MessageResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function login(payload: {
  login_method: LoginMethod
  identifier: string
  password: string
}) {
  return apiFetch<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function logout() {
  return apiFetch<MessageResponse>('/auth/logout', { method: 'POST' })
}

export function getSession() {
  return apiFetch<SessionStateResponse>('/auth/me')
}

export function forgotPasswordStart(accountId: string) {
  return apiFetch<ForgotPasswordStartResponse>('/auth/forgot-password/start', {
    method: 'POST',
    body: JSON.stringify({ account_id: accountId }),
  })
}

export function forgotPasswordReset(payload: {
  account_id: string
  security_answer: string
  new_password: string
  confirm_password: string
}) {
  return apiFetch<MessageResponse>('/auth/forgot-password/reset', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function changePassword(payload: {
  old_password: string
  new_password: string
  confirm_password: string
}) {
  return apiFetch<MessageResponse>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getMe() {
  return apiFetch<PrivateProfile>('/me')
}

export function updateProfile(payload: { username: string; bio: string }) {
  return apiFetch<PrivateProfile>('/me/profile', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function uploadAvatar(formData: FormData) {
  return apiFetch<PrivateProfile>('/me/avatar', {
    method: 'POST',
    body: formData,
  })
}

export function deleteAvatar() {
  return apiFetch<MessageResponse>('/me/avatar', { method: 'DELETE' })
}

export function getMyPosts() {
  return apiFetch<PaginatedPosts>('/me/posts')
}

export function getMyFavorites() {
  return apiFetch<PaginatedPosts>('/me/favorites')
}

export function getMyLikes() {
  return apiFetch<PaginatedPosts>('/me/likes')
}

export function getPublicUser(userId: string) {
  return apiFetch<PublicAuthorProfile>(`/users/${userId}`)
}

export function getPublicUserPosts(userId: string) {
  return apiFetch<PaginatedPosts>(`/users/${userId}/posts`)
}

export function ensurePostSummaries(response: PaginatedPosts | { items: PostSummary[] }) {
  return response.items
}
