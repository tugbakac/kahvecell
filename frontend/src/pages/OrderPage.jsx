import { ArrowLeft, ArrowRight, Coffee, Minus, Plus, ShoppingBag } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'

export default function OrderPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const shopId = searchParams.get('shop')
  const initialProductId = searchParams.get('product')
  const [shop, setShop] = useState(null)
  const [productId, setProductId] = useState(initialProductId || '')
  const [size, setSize] = useState('M')
  const [sugar, setSugar] = useState(1)
  const [milk, setMilk] = useState('WHOLE')
  const [shots, setShots] = useState(0)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(Boolean(shopId))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(shopId ? '' : 'Sipariş için önce bir dükkan seçmelisin.')

  useEffect(() => {
    let active = true
    if (!shopId) {
      return () => {
        active = false
      }
    }
    api.get(`/shops/${shopId}`)
      .then((response) => {
        if (!active) return
        const shopData = response.data.data
        setShop(shopData)
        if (!initialProductId && shopData.menu.length) {
          setProductId(String(shopData.menu[0].id))
        }
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError, 'Dükkan menüsü yüklenemedi.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [shopId, initialProductId])

  const selectedProduct = useMemo(
    () => shop?.menu.find((product) => String(product.id) === String(productId)),
    [shop, productId],
  )

  async function submitOrder(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const response = await api.post('/orders', {
        shop_id: Number(shopId),
        product_id: Number(productId),
        size,
        sugar_level: sugar,
        milk_type: milk,
        extra_shots: shots,
        notes: notes.trim() || null,
      })
      navigate(`/orders/${response.data.data.order.id}/qr`, {
        state: { order: response.data.data.order },
      })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Sipariş oluşturulamadı.'))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <div className="loading-panel">Sipariş ekranı hazırlanıyor…</div>
  if (!shop) {
    return (
      <div className="empty-state">
        <h2>Dükkan seçilmedi</h2>
        <p>{error}</p>
        <button className="button button-primary" onClick={() => navigate('/')} type="button">
          Dükkanları keşfet
        </button>
      </div>
    )
  }

  return (
    <div className="page-stack narrow-page">
      <button className="back-link" type="button" onClick={() => navigate(`/shops/${shop.id}`)}>
        <ArrowLeft size={17} /> Menüye dön
      </button>
      <div className="page-title-block">
        <span className="eyebrow">SANA ÖZEL HAZIRLANACAK</span>
        <h1>Siparişini oluştur</h1>
        <p>{shop.name} · Abonelik kahve hakkınla öde</p>
      </div>

      <form className="order-form-card" onSubmit={submitOrder}>
        <div className="order-product-heading">
          <span className="large-product-icon"><Coffee size={26} /></span>
          <div>
            <span className="product-category">MENÜDEN SEÇ</span>
            <h2>{selectedProduct?.name || 'Kahveni seç'}</h2>
            <span>{selectedProduct ? `${selectedProduct.price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺ · 1 abonelik hakkı` : 'Bir ürün seç'}</span>
          </div>
        </div>

        <div className="form-section">
          <label htmlFor="product">Kahve</label>
          <select id="product" value={productId} onChange={(event) => setProductId(event.target.value)} required>
            {shop.menu.map((product) => (
              <option value={product.id} key={product.id}>{product.name}</option>
            ))}
          </select>
        </div>

        <div className="form-section">
          <span className="form-label">Boyut</span>
          <div className="choice-row">
            {['S', 'M', 'L'].map((value) => (
              <button
                className={`choice-chip${size === value ? ' selected' : ''}`}
                key={value}
                onClick={() => setSize(value)}
                type="button"
              >
                {value}
              </button>
            ))}
          </div>
        </div>

        <div className="order-options-grid">
          <div className="form-section">
            <label htmlFor="milk">Süt tercihi</label>
            <select id="milk" value={milk} onChange={(event) => setMilk(event.target.value)}>
              <option value="WHOLE">Normal süt</option>
              <option value="LACTOSE_FREE">Laktozsuz</option>
              <option value="OAT">Yulaf sütü</option>
              <option value="ALMOND">Badem sütü</option>
              <option value="NONE">Sütsüz</option>
            </select>
          </div>
          <div className="form-section">
            <span className="form-label">Şeker</span>
            <div className="stepper">
              <button type="button" aria-label="Şekeri azalt" onClick={() => setSugar((value) => Math.max(0, value - 1))}><Minus size={15} /></button>
              <strong>{sugar}</strong>
              <button type="button" aria-label="Şekeri artır" onClick={() => setSugar((value) => Math.min(5, value + 1))}><Plus size={15} /></button>
            </div>
          </div>
        </div>

        <div className="form-section">
          <span className="form-label">Ek shot</span>
          <div className="stepper">
            <button type="button" aria-label="Shot azalt" onClick={() => setShots((value) => Math.max(0, value - 1))}><Minus size={15} /></button>
            <strong>{shots}</strong>
            <button type="button" aria-label="Shot artır" onClick={() => setShots((value) => Math.min(3, value + 1))}><Plus size={15} /></button>
          </div>
        </div>

        <div className="form-section">
          <label htmlFor="notes">Dükkana not <span>(isteğe bağlı)</span></label>
          <textarea
            id="notes"
            maxLength={500}
            placeholder="Siparişinle ilgili bir not ekle"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
          />
        </div>

        {error && <div className="form-error" role="alert">{error}</div>}

        <div className="order-submit-row">
          <div><ShoppingBag size={18} /><span>Ödenecek</span><strong>1 kahve hakkı</strong></div>
          <button className="button button-primary" type="submit" disabled={busy || !selectedProduct}>
            {busy ? 'Sipariş veriliyor…' : 'Siparişi onayla'}
            {!busy && <ArrowRight size={17} />}
          </button>
        </div>
      </form>
    </div>
  )
}
