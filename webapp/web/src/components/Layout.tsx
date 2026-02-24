import { Link, Outlet, useLocation } from 'react-router-dom'
import { TrendingUp, ScanLine, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { path: '/', label: '首页', icon: TrendingUp },
  { path: '/scanner', label: '扫描', icon: ScanLine },
  { path: '/reports', label: '报告', icon: FileText },
]

export function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-50 border-b bg-white shadow-sm">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-red-600" />
            <span className="text-lg font-bold">A股深度分析</span>
          </Link>
          
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-gray-100 text-gray-900'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>

      {/* 底部 */}
      <footer className="border-t bg-white py-4 text-center text-sm text-gray-500">
        A股深度分析系统 · 仅供学习研究，不构成投资建议
      </footer>
    </div>
  )
}
