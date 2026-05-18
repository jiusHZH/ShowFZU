export type LoginMethod = 'account_id' | 'username'

export type PostCategory =
  | 'Campus Landmark'
  | 'Study Space'
  | 'Student Life'
  | 'Food and Cafe'
  | 'Sports and Leisure'
  | 'Digital Memory'

export type MediaType = 'image' | 'video'

export interface UserSummary {
  id: string
  username: string
  avatar_url: string | null
  bio: string | null
}

export interface PrivateProfile {
  id: string
  account_id: string
  username: string
  avatar_url: string | null
  bio: string | null
  posts_count: number
  favorites_count: number
  likes_count: number
}

export interface SessionStateResponse {
  authenticated: boolean
  user: PrivateProfile | null
}

export interface AuthResponse {
  message: string
  user: PrivateProfile
}

export interface MessageResponse {
  message: string
}

export interface InteractionState {
  active: boolean
  count: number
}

export interface PostMediaItem {
  id: string
  type: MediaType
  url: string
  thumbnail_url: string | null
  mime_type: string
  size_bytes: number
  sort_order: number
}

export interface PostSummary {
  id: string
  title: string
  body_excerpt: string | null
  category: PostCategory
  cover_url: string | null
  cover_source: string
  published_at: string
  updated_at: string
  author: UserSummary
  like_count: number
  favorite_count: number
  has_video: boolean
  image_count: number
}

export interface PostDetail extends PostSummary {
  body: string | null
  media: PostMediaItem[]
  comment_count: number
  is_liked: boolean
  is_favorited: boolean
  can_edit: boolean
}

export interface PaginatedPosts {
  items: PostSummary[]
  total: number
  page: number
  page_size: number
}

export interface CommentNode {
  id: string
  body: string
  is_deleted: boolean
  created_at: string
  author: UserSummary
  replies: CommentNode[]
}

export interface CommentsResponse {
  items: CommentNode[]
}

export interface PublicAuthorProfile {
  user: UserSummary
  posts_count: number
  total_likes_received: number
}

export interface ForgotPasswordStartResponse {
  security_question: string
}

export interface OfficialGuideItem {
  id: string
  name: string
  description: string
  atmosphere: string
  imageUrl: string
  imageAlt: string
  sortOrder: number
}

export interface OfficialGuideData {
  hero: {
    title: string
    subtitle: string
    imageUrl: string
    imageAlt: string
  }
  items: OfficialGuideItem[]
  sourceDocs: string[]
}

