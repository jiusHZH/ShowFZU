import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Avatar } from '@/components/Avatar'
import { PostCard } from '@/components/PostCard'
import { UploadPicker } from '@/components/UploadPicker'
import { useAuth } from '@/context/useAuth'
import {
  changePassword,
  deleteAvatar,
  getMe,
  getMyFavorites,
  getMyLikes,
  getMyPosts,
  logout,
  updateProfile,
  uploadAvatar,
} from '@/lib/api'
import type { PaginatedPosts, PrivateProfile } from '@/types/api'

function ProfileCollectionPage({
  title,
  eyebrow,
  description,
  loader,
}: {
  title: string
  eyebrow: string
  description: string
  loader: () => Promise<PaginatedPosts>
}) {
  const [response, setResponse] = useState<PaginatedPosts | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const payload = await loader()
        if (!cancelled) {
          setResponse(payload)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load items.')
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [loader])

  return (
    <div className="stack-lg">
      <header className="page-intro">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </header>
      {error ? <p className="error-banner">{error}</p> : null}
      <div className="post-grid">
        {response?.items.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
      {response && response.items.length === 0 ? <p className="empty-state">Nothing to show here yet.</p> : null}
    </div>
  )
}

export function ProfilePage() {
  const navigate = useNavigate()
  const { user, setUser } = useAuth()
  const [profile, setProfile] = useState<PrivateProfile | null>(user)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const loadProfile = async () => {
      try {
        const payload = await getMe()
        if (!cancelled) {
          setProfile(payload)
          setUser(payload)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load your profile.')
        }
      }
    }
    void loadProfile()
    return () => {
      cancelled = true
    }
  }, [setUser])

  const handleLogout = async () => {
    await logout()
    setUser(null)
    navigate('/')
  }

  if (error) {
    return <p className="error-banner">{error}</p>
  }

  if (!profile) {
    return <p>Loading profile…</p>
  }

  return (
    <div className="stack-lg">
      <section className="author-hero">
        <div className="author-hero__identity">
          <Avatar user={profile} size="lg" />
          <div>
            <span className="eyebrow">Private profile area</span>
            <h1>{profile.username}</h1>
            <p>{profile.bio || 'Add a short bio to describe your public campus perspective.'}</p>
            <small>Account ID: {profile.account_id}</small>
          </div>
        </div>
        <dl className="author-hero__stats">
          <div>
            <dt>Posts</dt>
            <dd>{profile.posts_count}</dd>
          </div>
          <div>
            <dt>Favorites</dt>
            <dd>{profile.favorites_count}</dd>
          </div>
          <div>
            <dt>Likes</dt>
            <dd>{profile.likes_count}</dd>
          </div>
        </dl>
      </section>
      <div className="action-grid">
        <Link className="action-tile" to="/profile/posts">
          <strong>My Posts</strong>
          <span>Edit or remove your published stories.</span>
        </Link>
        <Link className="action-tile" to="/profile/favorites">
          <strong>My Favorites</strong>
          <span>Posts you saved for later.</span>
        </Link>
        <Link className="action-tile" to="/profile/likes">
          <strong>My Likes</strong>
          <span>Posts you reacted to most recently.</span>
        </Link>
        <Link className="action-tile" to="/profile/edit">
          <strong>Edit Profile</strong>
          <span>Change username, bio, and avatar.</span>
        </Link>
        <Link className="action-tile" to="/profile/change-password">
          <strong>Change Password</strong>
          <span>Validate the old password before replacing it.</span>
        </Link>
      </div>
      <div className="button-row">
        <button className="button button--ghost" onClick={() => void handleLogout()} type="button">
          Logout
        </button>
      </div>
    </div>
  )
}

export function MyPostsPage() {
  return (
    <ProfileCollectionPage
      title="My Posts"
      eyebrow="Private feed"
      description="Your published posts in reverse chronological order."
      loader={getMyPosts}
    />
  )
}

export function MyFavoritesPage() {
  return (
    <ProfileCollectionPage
      title="My Favorites"
      eyebrow="Saved posts"
      description="Posts you favorited, sorted by the time you saved them."
      loader={getMyFavorites}
    />
  )
}

export function MyLikesPage() {
  return (
    <ProfileCollectionPage
      title="My Likes"
      eyebrow="Liked posts"
      description="Posts you liked, sorted by the time you reacted."
      loader={getMyLikes}
    />
  )
}

export function EditProfilePage() {
  const { user, setUser } = useAuth()
  const [username, setUsername] = useState(user?.username ?? '')
  const [bio, setBio] = useState(user?.bio ?? '')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleProfileSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    try {
      const payload = await updateProfile({ username, bio })
      setUser(payload)
      setMessage('Profile updated.')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not update profile.')
    }
  }

  const handleAvatarUpload = async () => {
    if (!avatarFile) return
    const formData = new FormData()
    formData.append('avatar', avatarFile)
    try {
      const payload = await uploadAvatar(formData)
      setUser(payload)
      setMessage('Avatar uploaded.')
      setAvatarFile(null)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not upload avatar.')
    }
  }

  const handleAvatarDelete = async () => {
    try {
      await deleteAvatar()
      if (user) {
        setUser({ ...user, avatar_url: null })
      }
      setMessage('Avatar removed.')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not remove avatar.')
    }
  }

  return (
    <div className="editor-layout">
      <header className="page-intro">
        <span className="eyebrow">Edit profile</span>
        <h1>Update the public identity attached to every past post and comment.</h1>
      </header>
      <form className="editor-form" onSubmit={(event) => void handleProfileSubmit(event)}>
        <label className="field">
          <span>Username</span>
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label className="field">
          <span>Bio</span>
          <textarea rows={5} value={bio} onChange={(event) => setBio(event.target.value)} />
        </label>
        <div className="field">
          <span>Avatar image</span>
          <UploadPicker
            accept=".jpg,.jpeg,.png"
            actionText="Choose avatar"
            emptyText="JPG, JPEG, or PNG - up to 2 MB"
            selectedItems={avatarFile ? [avatarFile.name] : []}
            onChange={(files) => setAvatarFile(files?.[0] ?? null)}
            onRemove={() => setAvatarFile(null)}
          />
        </div>
        {message ? <p className="success-banner">{message}</p> : null}
        {error ? <p className="error-banner">{error}</p> : null}
        <div className="button-row">
          <button className="button button--primary" type="submit">
            Save profile
          </button>
          <button className="button button--ghost" onClick={() => void handleAvatarUpload()} type="button">
            Upload avatar
          </button>
          <button className="button button--ghost" onClick={() => void handleAvatarDelete()} type="button">
            Remove avatar
          </button>
        </div>
      </form>
    </div>
  )
}

export function ChangePasswordPage() {
  const [form, setForm] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    try {
      const response = await changePassword(form)
      setMessage(response.message)
      setForm({
        old_password: '',
        new_password: '',
        confirm_password: '',
      })
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not change password.')
    }
  }

  return (
    <div className="editor-layout">
      <header className="page-intro">
        <span className="eyebrow">Change password</span>
        <h1>Confirm the current password before replacing it.</h1>
      </header>
      <form className="editor-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="field">
          <span>Old password</span>
          <input
            type="password"
            value={form.old_password}
            onChange={(event) => setForm((current) => ({ ...current, old_password: event.target.value }))}
          />
        </label>
        <label className="field">
          <span>New password</span>
          <input
            type="password"
            value={form.new_password}
            onChange={(event) => setForm((current) => ({ ...current, new_password: event.target.value }))}
          />
        </label>
        <label className="field">
          <span>Confirm new password</span>
          <input
            type="password"
            value={form.confirm_password}
            onChange={(event) => setForm((current) => ({ ...current, confirm_password: event.target.value }))}
          />
        </label>
        {message ? <p className="success-banner">{message}</p> : null}
        {error ? <p className="error-banner">{error}</p> : null}
        <div className="button-row">
          <button className="button button--primary" type="submit">
            Update password
          </button>
        </div>
      </form>
    </div>
  )
}
