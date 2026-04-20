import { useState } from 'react'

export default function SearchBar({ onSearch, loading }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const q = value.trim()
    if (q) onSearch(q)
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        value={value}
        onChange={e => setValue(e.target.value)}
        placeholder="Search by paper title or keywords…"
        disabled={loading}
        autoFocus
      />
      <button type="submit" disabled={loading || !value.trim()}>
        {loading ? 'Searching…' : 'Search'}
      </button>
    </form>
  )
}
