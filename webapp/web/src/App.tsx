import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'
import { Home } from '@/pages/Home'
import { Analysis } from '@/pages/Analysis'
import { Scanner } from '@/pages/Scanner'
import { Reports } from '@/pages/Reports'
import { SharedReport } from '@/pages/SharedReport'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="analysis/:tsCode" element={<Analysis />} />
            <Route path="scanner" element={<Scanner />} />
            <Route path="reports" element={<Reports />} />
          </Route>
          {/* 分享报告页面（无布局） */}
          <Route path="/r/:reportId" element={<SharedReport />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
