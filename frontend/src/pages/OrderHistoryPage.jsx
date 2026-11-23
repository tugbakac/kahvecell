import { ArrowRight, Coffee, History, MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'

const statusLabels = {
  PENDING: 'Sipariş alındı',
  ACCEPTED: 'Kabul edildi',
  PREPARING: 'Hazırlanıyor',
  READY: 'Hazır',
  DELIVERED: 'Teslim edildi',
  CANCELLED: 'İptal edildi',
}

export default function OrderHistoryPage() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api.get('/orders/history')
      .then((response) => {
        if (active) setOrders(response.data.data)
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError, 'Sipariş geçmişi yüklenemedi.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="page-stack narrow-page">
      <div className="page-title-block">
        <span className="eyebrow">KAHVE ANILARIN</span>
        <h1>Sipariş geçmişim</h1>
        <p>Son kahve molaların ve sipariş durumların burada.</p>
      </div>

      {error && <div className="inline-error" role="alert">{error}</div>}
      {loading && <div className="loading-panel">Siparişlerin yükleniyor…</div>}
      {!loading && !error && orders.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon"><History size={27} /></span>
          <h2>İlk kahve molanı planla</h2>
          <p>Henüz bir siparişin yok. Yakınındaki dükkanları keşfederek başlayabilirsin.</p>
          <Link className="button button-primary" to="/">Dükkanları keşfet <ArrowRight size={17} /></Link>
        </div>
      )}
      {!loading && orders.length > 0 && (
        <div className="history-list">
          {orders.map((order) => (
            <article className="history-card" key={order.id}>
              <span className="history-coffee-icon"><Coffee size={21} /></span>
              <div className="history-main">
                <div className="history-title-row">
                  <strong>{order.product.name}</strong>
                  <span className={`status-pill status-${order.status.toLowerCase()}`}>
                    {statusLabels[order.status] || order.status}
                  </span>
                </div>
                <span className="history-shop"><MapPin size={14} /> {order.shop.name}</span>
                <span className="history-date">
                  {new Date(order.created_at).toLocaleString('tr-TR', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </span>
              </div>
              <Link className="icon-action" to={`/orders/${order.id}/qr`} aria-label="Sipariş QR kodunu gör">
                <ArrowRight size={18} />
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
