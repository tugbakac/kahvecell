import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { useAuth } from './auth/AuthContext'
import AppShell from './components/AppShell'
import RequireAuth from './components/RequireAuth'

const AuthPage = lazy(() => import('./pages/AuthPage'))
const HomePage = lazy(() => import('./pages/HomePage'))
const OrderHistoryPage = lazy(() => import('./pages/OrderHistoryPage'))
const OrderPage = lazy(() => import('./pages/OrderPage'))
const OrderQrPage = lazy(() => import('./pages/OrderQrPage'))
const ShopDetailPage = lazy(() => import('./pages/ShopDetailPage'))
const SubscriptionPage = lazy(() => import('./pages/SubscriptionPage'))

function GuestRoute({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/" replace /> : children
}

export default function App() {
  return (
    <Suspense fallback={<div className="loading-panel route-loading">KahveCell açılıyor…</div>}>
      <Routes>
        <Route path="/login" element={<GuestRoute><AuthPage /></GuestRoute>} />
        <Route path="/register" element={<GuestRoute><AuthPage mode="register" /></GuestRoute>} />
        <Route path="/" element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={<HomePage />} />
          <Route path="shops/:shopId" element={<ShopDetailPage />} />
          <Route path="orders/new" element={<OrderPage />} />
          <Route path="orders/history" element={<OrderHistoryPage />} />
          <Route path="orders/:orderId/qr" element={<OrderQrPage />} />
          <Route path="subscription" element={<SubscriptionPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
