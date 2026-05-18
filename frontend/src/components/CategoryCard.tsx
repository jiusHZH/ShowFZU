import { Link } from 'react-router-dom'

import type { CategoryMeta } from '@/data/categories'

interface CategoryCardProps {
  category: CategoryMeta
}

export function CategoryCard({ category }: CategoryCardProps) {
  return (
    <Link className="category-card" to={`/categories/${category.slug}`}>
      <img className="category-card__image" src={category.imageUrl} alt={category.name} />
      <div className="category-card__overlay" />
      <div className="category-card__content">
        <span className="eyebrow">Category</span>
        <h3>{category.name}</h3>
        <p>{category.description}</p>
      </div>
    </Link>
  )
}

