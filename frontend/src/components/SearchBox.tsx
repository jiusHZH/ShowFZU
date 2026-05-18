import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

interface SearchBoxProps {
  initialValue?: string
}

export function SearchBox({ initialValue = '' }: SearchBoxProps) {
  const navigate = useNavigate()
  const [value, setValue] = useState(initialValue)

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const query = value.trim()
    navigate(query ? `/search?q=${encodeURIComponent(query)}` : '/search')
  }

  return (
    <form className="search-box" onSubmit={handleSubmit}>
      <input
        aria-label="Search posts"
        className="search-box__input"
        placeholder="Search titles, body text, or authors"
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      <button className="search-box__button" type="submit">
        Search
      </button>
    </form>
  )
}
