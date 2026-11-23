import { ArrowLeft, ArrowRight, Clock3, MapPin, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'

export default function ShopDetailPage() {
  const { shopId } = useParams()
  const navigate = useNavigate()
  const [shop, setShop] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api.get(`/shops/${shopId}`)
      .then((response) => {
        if (active) setShop(response.data.data)
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError, 'Dükkan bilgisi alınamadı.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [shopId])

  if (loading) return <div className="loading-panel">Dükkan bilgileri yükleniyor…</div>
  if (error || !shop) {
    return (
      <div className="empty-state">
        <h2>Dükkan açılamadı</h2>
        <p>{error || 'Aradığın dükkan bulunamadı.'}</p>
        <Link className="button button-primary" to="/">Ana sayfaya dön</Link>
      </div>
    )
  }

  return (
    <div className="page-stack narrow-page">
      <button className="back-link" type="button" onClick={() => navigate(-1)}>
        <ArrowLeft size={17} /> Dükkanlara dön
      </button>
      <section className="shop-detail-hero">
        <div className="shop-detail-art"><span><MapPin size={30} /></span></div>
        <div className="shop-detail-copy">
          <span className="eyebrow">KAHVECELL ANLAŞMALI DÜKKANI</span>
          <h1>{shop.name}</h1>
          <p><MapPin size={16} /> {shop.address}</p>
          <div className="shop-meta">
            <span><Star size={15} fill="currentColor" /> {shop.rating ?? 'Yeni'}</span>
            {shop.distance_km != null && <span>{shop.distance_km} km uzakta</span>}
            <span><Clock3 size={15} /> Açık saatler bilgisi</span>
          </div>
        </div>
      </section>

      <section className="menu-section">
        <div className="section-heading">
          <div>
            <span className="eyebrow">TADINI SEÇ</span>
            <h2>Menü</h2>
          </div>
          <span className="menu-count">{shop.menu.length} ürün</span>
        </div>
        {shop.menu.length === 0 ? (
          <div className="empty-card">Bu dükkanın menüsünde şu an ürün bulunmuyor.</div>
        ) : (
          <div className="menu-grid">
            {shop.menu.map((product) => (
              <article className="menu-card" key={product.id}>
                <div className="menu-product-icon"><span><span /></span></div>
                <div className="menu-product-details">
                  <span className="product-category">KAHVE</span>
                  <h3>{product.name}</h3>
                  <p>{product.description || 'Özenle hazırlanmış kahve molası.'}</p>
                  <div className="menu-price-row">
                    <strong>{product.price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺</strong>
                    <button
                      className="button button-dark button-small"
                      onClick={() => navigate(`/orders/new?shop=${shop.id}&product=${product.id}`)}
                      type="button"
                    >
                      Seç <ArrowRight size={15} />
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
