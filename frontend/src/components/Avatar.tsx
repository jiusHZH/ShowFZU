import type { UserSummary } from '@/types/api'

interface AvatarProps {
  user: Pick<UserSummary, 'avatar_url' | 'username'>
  size?: 'sm' | 'md' | 'lg'
}

export function Avatar({ user, size = 'md' }: AvatarProps) {
  const initial = user.username.slice(0, 1).toUpperCase()
  return user.avatar_url ? (
    <img className={`avatar avatar--${size}`} src={user.avatar_url} alt={user.username} />
  ) : (
    <div className={`avatar avatar--${size} avatar--fallback`} aria-hidden="true">
      {initial}
    </div>
  )
}

