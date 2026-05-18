import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { Avatar } from '@/components/Avatar'
import { CategoryCard } from '@/components/CategoryCard'
import { CategoryTabs } from '@/components/CategoryTabs'
import { PostCard } from '@/components/PostCard'
import { categoryList, getCategoryBySlug, getSlugForCategory } from '@/data/categories'
import officialGuideData from '@/data/officialGuide.json'
import { getPublicUser, getPublicUserPosts, listPosts } from '@/lib/api'
import { formatDate } from '@/lib/format'
import type { OfficialGuideData, PaginatedPosts, PostSummary, PublicAuthorProfile } from '@/types/api'

const featurePoints = [
  { label: 'Main Gate', slug: 'campus-landmark' },
  { label: 'Library', slug: 'study-space' },
  { label: 'Fuyou Pavilion', slug: 'study-space' },
  { label: 'Campus Scenery', slug: 'campus-landmark' },
]

export function HomePage() {
  const [posts, setPosts] = useState<PostSummary[]>([])
  const [activeCategory, setActiveCategory] = useState('all')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const loadPosts = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const category = activeCategory === 'all' ? undefined : getCategoryBySlug(activeCategory)?.name
        const response = await listPosts({ category, pageSize: 6 })
        if (!cancelled) {
          setPosts(response.items)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load posts.')
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadPosts()
    return () => {
      cancelled = true
    }
  }, [activeCategory])

  return (
    <div className="stack-xl">
      <section className="hero-banner">
        <img className="hero-banner__image" src="/categories/home-hero.jpg" alt="FZU campus lake and skyline" />
        <div className="hero-banner__scrim" />
        <div className="hero-banner__content">
          <span className="eyebrow">Fuzhou University in view</span>
          <h1>Architecture, atmosphere, and campus stories on one English-language stage.</h1>
          <p>
            Explore official campus landmarks first, then move through study spaces, food diaries, sports venues, and digital memory posted by the community.
          </p>
          <div className="hero-banner__actions">
            <Link className="button button--primary" to="/official-guide">
              Explore Official FZU Guide
            </Link>
            <Link className="button button--ghost" to="/categories">
              Browse All Categories
            </Link>
          </div>
          <div className="hero-banner__points">
            {featurePoints.map((point) => (
              <Link key={point.label} to={`/categories/${point.slug}`}>
                {point.label}
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="stack-md">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Six fixed categories</span>
            <h2>Find the campus angle you want first.</h2>
          </div>
          <Link className="text-link" to="/categories">
            Open categories
          </Link>
        </div>
        <div className="category-grid">
          {categoryList.map((category) => (
            <CategoryCard key={category.slug} category={category} />
          ))}
        </div>
      </section>

      <section className="stack-md">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Latest feed</span>
            <h2>Fresh posts, filtered by category without leaving home.</h2>
          </div>
        </div>
        <CategoryTabs
          activeCategory={activeCategory}
          categories={categoryList}
          onSelect={setActiveCategory}
        />
        {isLoading ? <p>Loading posts...</p> : null}
        {error ? <p className="error-banner">{error}</p> : null}
        {!isLoading && posts.length === 0 ? <p className="empty-state">No posts yet in this category.</p> : null}
        <div className="post-grid">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      </section>
    </div>
  )
}

export function CategoriesPage() {
  return (
    <div className="stack-lg">
      <header className="page-intro">
        <span className="eyebrow">Categories</span>
        <h1>The six ways ShowFZU reads campus life.</h1>
        <p>
          Every post belongs to one primary category. The structure stays fixed so browsing, search, and profile history remain readable over time.
        </p>
      </header>
      <div className="category-grid">
        {categoryList.map((category) => (
          <CategoryCard key={category.slug} category={category} />
        ))}
      </div>
    </div>
  )
}

export function CategoryPage() {
  const { slug } = useParams()
  const category = getCategoryBySlug(slug)
  const [response, setResponse] = useState<PaginatedPosts | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!category) return
    let cancelled = false
    const loadCategory = async () => {
      setError(null)
      try {
        const payload = await listPosts({ category: category.name, pageSize: 12 })
        if (!cancelled) {
          setResponse(payload)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load category.')
        }
      }
    }
    void loadCategory()
    return () => {
      cancelled = true
    }
  }, [category])

  if (!category) {
    return <NotFoundPage />
  }

  return (
    <div className="stack-lg">
      <section className="category-hero">
        <img className="category-hero__image" src={category.imageUrl} alt={category.name} />
        <div className="category-hero__scrim" />
        <div className="category-hero__content">
          <span className="eyebrow">Category</span>
          <h1>{category.name}</h1>
          <p>{category.description}</p>
        </div>
      </section>
      {error ? <p className="error-banner">{error}</p> : null}
      <div className="post-grid">
        {response?.items.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
      {response && response.items.length === 0 ? <p className="empty-state">No posts have been published in this category yet.</p> : null}
    </div>
  )
}

export function SearchResultsPage() {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q')?.trim() ?? ''
  const [response, setResponse] = useState<PaginatedPosts | null>(null)
  const [error, setError] = useState<string | null>(null)
  const visibleResponse = query ? response : null
  const visibleError = query ? error : null

  useEffect(() => {
    if (!query) {
      return
    }
    let cancelled = false
    const search = async () => {
      setError(null)
      try {
        const payload = await listPosts({ q: query, pageSize: 12 })
        if (!cancelled) {
          setResponse(payload)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Search failed.')
        }
      }
    }
    void search()
    return () => {
      cancelled = true
    }
  }, [query])

  return (
    <div className="stack-lg">
      <header className="page-intro">
        <span className="eyebrow">Search</span>
        <h1>{query ? `Results for "${query}"` : 'Search the campus feed'}</h1>
        <p>Search includes post titles, body text, and public author usernames. The official guide stays outside search indexing.</p>
      </header>
      {visibleError ? <p className="error-banner">{visibleError}</p> : null}
      {query ? (
        <>
          <div className="post-grid">
            {visibleResponse?.items.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
          {visibleResponse && visibleResponse.items.length === 0 ? <p className="empty-state">Nothing matched that keyword.</p> : null}
        </>
      ) : (
        <p className="empty-state">Enter a keyword in the search bar to begin.</p>
      )}
    </div>
  )
}

export function OfficialGuidePage() {
  const guide = officialGuideData as OfficialGuideData

  return (
    <div className="stack-xl">
      <section className="official-hero">
        <img className="official-hero__image" src={guide.hero.imageUrl} alt={guide.hero.imageAlt} />
        <div className="official-hero__scrim" />
        <div className="official-hero__content">
          <span className="eyebrow">Official FZU Introduction</span>
          <h1>{guide.hero.title}</h1>
          <p>{guide.hero.subtitle}</p>
        </div>
      </section>

      <section className="stack-md">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Photography exhibition</span>
            <h2>Architecture, water, and study atmosphere arranged as a static editorial sequence.</h2>
          </div>
        </div>
        <div className="official-guide">
          {guide.items.map((item, index) => (
            <article
              key={item.id}
              className={index % 2 === 0 ? 'official-guide__item' : 'official-guide__item is-reversed'}
            >
              <img src={item.imageUrl} alt={item.imageAlt} />
              <div>
                <span className="eyebrow">Official guide section {item.sortOrder}</span>
                <h3>{item.name}</h3>
                <p>{item.description}</p>
                <p className="official-guide__atmosphere">{item.atmosphere}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

export function PublicAuthorPage() {
  const { userId } = useParams()
  const [profile, setProfile] = useState<PublicAuthorProfile | null>(null)
  const [posts, setPosts] = useState<PostSummary[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!userId) return
    let cancelled = false
    const loadProfile = async () => {
      setError(null)
      try {
        const [profilePayload, postsPayload] = await Promise.all([
          getPublicUser(userId),
          getPublicUserPosts(userId),
        ])
        if (!cancelled) {
          setProfile(profilePayload)
          setPosts(postsPayload.items)
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load author page.')
        }
      }
    }
    void loadProfile()
    return () => {
      cancelled = true
    }
  }, [userId])

  if (error) {
    return <p className="error-banner">{error}</p>
  }

  if (!profile) {
    return <p>Loading author profile...</p>
  }

  return (
    <div className="stack-lg">
      <section className="author-hero">
        <div className="author-hero__identity">
          <Avatar user={profile.user} size="lg" />
          <div>
            <span className="eyebrow">Public author page</span>
            <h1>{profile.user.username}</h1>
            <p>{profile.user.bio || 'No bio added yet.'}</p>
          </div>
        </div>
        <dl className="author-hero__stats">
          <div>
            <dt>Posts</dt>
            <dd>{profile.posts_count}</dd>
          </div>
          <div>
            <dt>Total Likes Received</dt>
            <dd>{profile.total_likes_received}</dd>
          </div>
        </dl>
      </section>
      <section className="stack-md">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Published posts</span>
            <h2>Public stories by this author.</h2>
          </div>
        </div>
        <div className="post-grid">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
        {posts.length === 0 ? <p className="empty-state">This author has not published any posts yet.</p> : null}
      </section>
    </div>
  )
}

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="page-intro">
      <span className="eyebrow">404</span>
      <h1>The page you asked for is not in this route map.</h1>
      <p>Use the home page, categories, or the official guide to get back into the site flow.</p>
      <div className="button-row">
        <button className="button button--primary" onClick={() => navigate('/') } type="button">
          Return Home
        </button>
        <Link className="button button--ghost" to="/official-guide">
          Open Official Guide
        </Link>
      </div>
    </div>
  )
}

export function CategoryMetaInline({ category }: { category: PostSummary['category'] }) {
  const slug = useMemo(() => getSlugForCategory(category), [category])
  return <Link to={`/categories/${slug}`}>{category}</Link>
}

export function AuthorStamp({ username, date }: { username: string; date: string }) {
  return (
    <p className="author-stamp">
      By <strong>{username}</strong> on {formatDate(date)}
    </p>
  )
}
