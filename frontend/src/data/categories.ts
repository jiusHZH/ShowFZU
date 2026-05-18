import type { PostCategory } from '@/types/api'

export interface CategoryMeta {
  slug: string
  name: PostCategory
  description: string
  imageUrl: string
}

export const categoryList: CategoryMeta[] = [
  {
    slug: 'campus-landmark',
    name: 'Campus Landmark',
    description: 'Formal campus landmarks, skyline anchors, and places that make FZU recognizable at a glance.',
    imageUrl: '/categories/campus-landmark.jpg',
  },
  {
    slug: 'study-space',
    name: 'Study Space',
    description: 'Libraries, reading corners, pavilion seats, and the spaces where focus settles in.',
    imageUrl: '/categories/study-space.jpg',
  },
  {
    slug: 'student-life',
    name: 'Student Life',
    description: 'The social tempo of campus life, from routines to shared events and everyday atmosphere.',
    imageUrl: '/categories/student-life.jpg',
  },
  {
    slug: 'food-and-cafe',
    name: 'Food and Cafe',
    description: 'Dining halls, campus snacks, and the places where conversations stretch past class time.',
    imageUrl: '/categories/food-and-cafe.jpg',
  },
  {
    slug: 'sports-and-leisure',
    name: 'Sports and Leisure',
    description: 'Performance venues, open-air movement, and the campus spaces built for release and rhythm.',
    imageUrl: '/categories/sports-and-leisure.jpg',
  },
  {
    slug: 'digital-memory',
    name: 'Digital Memory',
    description: 'Moments worth keeping: reflections, weather, light, and the textures that linger after the day ends.',
    imageUrl: '/categories/digital-memory.jpg',
  },
]

export const categoryMap = new Map(categoryList.map((category) => [category.slug, category]))

export function getCategoryBySlug(slug: string | undefined): CategoryMeta | undefined {
  return slug ? categoryMap.get(slug) : undefined
}

export function getSlugForCategory(category: PostCategory): string {
  return categoryList.find((item) => item.name === category)?.slug ?? 'categories'
}

