import { useState, useEffect, useRef } from 'react'
import { Search, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface StockSearchProps {
  onSelect: (tsCode: string) => void
}

interface StockResult {
  ts_code: string
  name: string
  industry?: string
}

export function StockSearch({ onSelect }: StockSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // 搜索防抖
  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }

    const timer = setTimeout(async () => {
      setIsLoading(true)
      try {
        const res = await fetch(`/api/stocks/search?q=${encodeURIComponent(query)}&limit=8`)
        if (res.ok) {
          const data = await res.json()
          setResults(data.results || [])
          setShowResults(true)
        }
      } catch (error) {
        console.error('搜索失败:', error)
      } finally {
        setIsLoading(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query])

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 键盘导航
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => Math.max(prev - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (selectedIndex >= 0 && results[selectedIndex]) {
        handleSelect(results[selectedIndex].ts_code)
      } else if (query.trim()) {
        // 直接使用输入的代码
        handleSelect(query.trim())
      }
    } else if (e.key === 'Escape') {
      setShowResults(false)
    }
  }

  const handleSelect = (tsCode: string) => {
    setShowResults(false)
    setQuery('')
    onSelect(tsCode)
  }

  const handleSubmit = () => {
    if (query.trim()) {
      handleSelect(query.trim())
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            ref={inputRef}
            type="text"
            placeholder="输入股票代码或名称，如 600519、茅台"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(-1)
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => results.length > 0 && setShowResults(true)}
            className="pl-9"
          />
          {isLoading && (
            <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-gray-400" />
          )}
        </div>
        <Button onClick={handleSubmit} className="bg-red-600 hover:bg-red-700">
          分析
        </Button>
      </div>

      {/* 搜索结果下拉 */}
      {showResults && results.length > 0 && (
        <div className="absolute top-full z-50 mt-1 w-full rounded-md border bg-white shadow-lg">
          {results.map((stock, index) => (
            <div
              key={stock.ts_code}
              className={cn(
                'flex cursor-pointer items-center justify-between px-4 py-2',
                index === selectedIndex ? 'bg-gray-100' : 'hover:bg-gray-50'
              )}
              onClick={() => handleSelect(stock.ts_code)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div>
                <span className="font-medium">{stock.name}</span>
                <span className="ml-2 text-sm text-gray-500">
                  {stock.ts_code.split('.')[0]}
                </span>
              </div>
              {stock.industry && (
                <span className="text-xs text-gray-400">{stock.industry}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
