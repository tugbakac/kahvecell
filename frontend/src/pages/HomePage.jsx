import {
  ArrowRight,
  Coffee,
  LocateFixed,
  MapPin,
  Search,
  Sparkles,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import ShopMap from '../components/ShopMap'

const KIZILAY = { lat: 39.9204, lng: 32.8549 }

function greeting() {
  const hour = new Date().getHours()
  if (hour < 11) return 'Günaydın'
  if (hour < 18) return 'Merhaba'
  return 'İyi akşamlar'
}

export default function HomePage() {
  const [shops, setShops] = useState([])
  const [subscription, setSubscription] = useState(null)
  const [orders, setOrders] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    async function loadDashboard() {
      setLoading(true)
      setError('')
      try {
        const [shopResponse, subscriptionResponse, orderResponse] = await Promise.all([
          api.get('/shops', { params: { lat: KIZILAY.lat, lng: KIZILAY.lng } }),
          api.get('/subscriptions/me'),
          api.get('/orders/history'),
        ])
        if (!active) return
        setShops(shopResponse.data.data)
        setSubscription(subscriptionResponse.data.data)
        setOrders(orderResponse.data.data)
      } catch (requestError) {
        if (active) setError(getErrorMessage(requestError, 'Ana sayfa yüklenemedi.'))
      } finally {
        if (active) setLoading(false)
      }
    }
    loadDashboard()
    return () => {
      active = false
    }
  }, [])

  const filteredShops = useMemo(() => {
    const term = search.trim().toLocaleLowerCase('tr-TR')
    if (!term) return shops
    return shops.filter((shop) =>
      `${shop.name} ${shop.address}`.toLocaleLowerCase('tr-TR').includes(term),
    )
  }, [shops, search])

  return (
    <div className="page-stack">
      <section className="welcome-row">
        <div>
          <span className="eyebrow">KAHVECELL DÜNYASINA HOŞ GELDİN</span>
          <h1>{greeting()}, kahve molan seni bekliyor.</h1>
          <p>Yakınındaki favori kahvecini bul, kahveni birkaç dokunuşla hazırla.</p>
        </div>
        <span className="date-pill"><Sparkles size={15} /> Bugün kendine iyi bak</span>
      </section>

      <section className="dashboard-hero">
        <div className="hero-copy">
          <span className="hero-kicker"><span /> ŞEHRİN KAHVE RİTMİ</span>
          <h2>İyi kahve,<br />iyi hissettirir.</h2>
          <p>Yakınındaki anlaşmalı kahvecileri keşfet ve sıranı beklemeden sipariş ver.</p>
          <a className="button button-yellow" href="#nearby">
            Dükkanları keşfet <ArrowRight size={17} />
          </a>
        </div>
        <div className="hero-coffee-art" aria-hidden="true">
          <span className="hero-sun" />
          <span className="hero-cup"><Coffee size={79} strokeWidth={1.15} /></span>
          <span className="hero-ring ring-a" />
          <span className="hero-ring ring-b" />
          <span className="hero-art-label">KAHVE MOLASI<br /><strong>HER AN GÜZEL</strong></span>
        </div>
      </section>

      <section className="quick-stats" aria-label="Hesap özeti">
        <article className="stat-card">
          <span className="stat-icon stat-yellow"><Coffee size={19} /></span>
          <div>
            <span className="stat-label">Kalan kahve hakkın</span>
            <strong>{loading ? '—' : subscription?.remaining_credits ?? (subscription ? 'Sınırsız' : '0')}</strong>
          </div>
          <Link to="/subscription" aria-label="Aboneliğe git"><ArrowRight size={17} /></Link>
        </article>
        <article className="stat-card">
          <span className="stat-icon stat-blue"><MapPin size={19} /></span>
          <div>
            <span className="stat-label">Yakınında dükkan</span>
            <strong>{loading ? '—' : shops.length}</strong>
          </div>
          <a href="#nearby" aria-label="Yakındaki dükkanlara git"><ArrowRight size={17} /></a>
        </article>
        <article className="stat-card">
          <span className="stat-icon stat-peach"><Sparkles size={19} /></span>
          <div>
            <span className="stat-label">Siparişlerin</span>
            <strong>{loading ? '—' : orders.length}</strong>
          </div>
          <Link to="/orders/history" aria-label="Sipariş geçmişine git"><ArrowRight size={17} /></Link>
        </article>
      </section>

      {error && <div className="inline-error" role="alert">{error}</div>}

      <section className="nearby-section" id="nearby">
        <div className="section-heading">
          <div>
            <span className="eyebrow">KONUMUNA YAKIN</span>
            <h2>Bugün nerede kahve içiyoruz?</h2>
          </div>
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label="Dükkan adı veya adresi ara"
              placeholder="Dükkan veya adres ara"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>

        <div className="discover-grid">
          <div className="map-card">
            <div className="map-card-heading">
              <span><LocateFixed size={16} /> Kızılay çevresi</span>
              <span className="map-live"><i /> Harita</span>
            </div>
            {loading ? (
              <div className="map-placeholder">Dükkanlar haritada yükleniyor…</div>
            ) : (
              <ShopMap shops={filteredShops} />
            )}
          </div>

          <div className="nearby-list">
            {loading && <div className="empty-card">Yakındaki dükkanlar yükleniyor…</div>}
            {!loading && filteredShops.length === 0 && (
              <div className="empty-card">
                <MapPin size={24} />
                <strong>Sonuç bulunamadı</strong>
                <span>Başka bir dükkan adı veya adres deneyebilirsin.</span>
              </div>
            )}
            {!loading && filteredShops.slice(0, 4).map((shop, index) => (
              <Link className="nearby-shop-card" to={`/shops/${shop.id}`} key={shop.id}>
                <span className={`shop-number number-${index + 1}`}>0{index + 1}</span>
                <span className="nearby-shop-info">
                  <strong>{shop.name}</strong>
                  <span>{shop.address}</span>
                  <small>
                    <MapPin size={12} />
                    {shop.distance_km != null ? `${shop.distance_km} km` : 'Ankara'}
                  </small>
                </span>
                <ArrowRight size={17} className="shop-arrow" />
              </Link>
            ))}
            {!loading && filteredShops.length > 4 && (
              <span className="list-footnote">Haritada {filteredShops.length} dükkan gösteriliyor.</span>
            )}
          </div>
        </div>
        <div className="section-foot">
          <Coffee size={15} /> Dükkan konumları seed verisinden gösterilmektedir.
        </div>
      </section>
    </div>
  )
}
