import type { CategoryMeta } from '@/data/categories'

interface CategoryTabsProps {
  activeCategory: string
  categories: CategoryMeta[]
  onSelect: (slug: string) => void
}

export function CategoryTabs({ activeCategory, categories, onSelect }: CategoryTabsProps) {
  return (
    <div className="category-tabs">
      <button
        className={activeCategory === 'all' ? 'category-tabs__tab is-active' : 'category-tabs__tab'}
        onClick={() => onSelect('all')}
        type="button"
      >
        Latest
      </button>
      {categories.map((category) => (
        <button
          key={category.slug}
          className={activeCategory === category.slug ? 'category-tabs__tab is-active' : 'category-tabs__tab'}
          onClick={() => onSelect(category.slug)}
          type="button"
        >
          {category.name}
        </button>
      ))}
    </div>
  )
}

