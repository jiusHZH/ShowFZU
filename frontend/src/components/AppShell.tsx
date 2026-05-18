import type { PropsWithChildren } from 'react'
import { Link, NavLink } from 'react-router-dom'

import { Avatar } from '@/components/Avatar'
import { SearchBox } from '@/components/SearchBox'
import { useAuth } from '@/context/useAuth'

export function AppShell({ children }: PropsWithChildren) {
  const { user } = useAuth()

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__brand-row">
          <Link className="brand" to="/">
            <span className="brand__crest">FZU</span>
            <span className="brand__text">
              <strong>ShowFZU</strong>
              <small>Campus showcase and community</small>
            </span>
          </Link>
          <nav className="topbar__nav">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/categories">Categories</NavLink>
            <NavLink to="/create-post">Create Post</NavLink>
            <NavLink to={user ? '/profile' : '/login'}>{user ? 'Profile' : 'Login'}</NavLink>
          </nav>
        </div>
        <div className="topbar__utility-row">
          <SearchBox />
          {user ? (
            <Link className="topbar__profile-link" to="/profile">
              <Avatar user={user} size="sm" />
              <span>{user.username}</span>
            </Link>
          ) : (
            <div className="topbar__hint">Guest mode: browse everything, sign in to participate.</div>
          )}
        </div>
      </header>
      <main className="page-shell">{children}</main>
      <footer className="footer">
        <p>ShowFZU presents Fuzhou University through official photography, student stories, and searchable campus memory.</p>
      </footer>
    </div>
  )
}
