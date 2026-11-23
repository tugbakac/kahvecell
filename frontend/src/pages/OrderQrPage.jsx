import { ArrowLeft, CheckCircle2, Clock3, Copy, MapPin, QrCode } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'

export default function OrderQrPage() {
  const { orderId } = useParams()
  const location = useLocation()
  const [order, setOrder] = useState(location.state?.order || null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (order) return
    let active = true
    api.get(`/orders/${orderId}`)
      .then((response) => {
        if (active) setOrder(response.data.data)
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError, 'Sipariş bulunamadı.'))
      })
    return () => {
      active = false
    }
  }, [order, orderId])

  async function copyPayload() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(order.qr_code, null, 2))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setError('QR içeriği panoya kopyalanamadı.')
    }
  }

  if (error) {
    return (
      <div className="empty-state">
        <h2>Sipariş açılamadı</h2>
        <p>{error}</p>
        <Link className="button button-primary" to="/orders/history">Siparişlerime dön</Link>
      </div>
    )
  }
  if (!order) return <div className="loading-panel">Sipariş ve QR kodu yükleniyor…</div>

  return (
    <div className="page-stack narrow-page">
      <Link className="back-link" to="/orders/history"><ArrowLeft size={17} /> Siparişlerim</Link>
      <section className="qr-page-card">
        <div className="qr-success-icon"><CheckCircle2 size={26} /></div>
        <span className="eyebrow">SİPARİŞİN ALINDI</span>
        <h1>Kahven hazırlanıyor.</h1>
        <p className="qr-page-subtitle">Dükkanda teslim alırken QR kodunu göster.</p>

        <div className="qr-frame">
          {order.qr_code ? (
            <QRCodeSVG
              value={JSON.stringify(order.qr_code)}
              size={220}
              level="H"
              includeMargin
              bgColor="#ffffff"
              fgColor="#14213d"
            />
          ) : (
            <div className="qr-missing"><QrCode size={42} /><span>Bu sipariş için QR bulunamadı.</span></div>
          )}
        </div>

        <div className="qr-order-number">
          <span>SİPARİŞ NUMARASI</span>
          <strong>#{String(order.id).padStart(5, '0')}</strong>
        </div>
        <div className="qr-order-details">
          <div><CoffeeMark /> <span>{order.product?.name || 'Kahve siparişi'}</span></div>
          <div><MapPin size={16} /> <span>{order.shop?.name || 'Anlaşmalı dükkan'}</span></div>
          <div><Clock3 size={16} /> <span>{order.status}</span></div>
        </div>
        {order.qr_code && (
          <button className="button button-outline button-wide" type="button" onClick={copyPayload}>
            {copied ? <CheckCircle2 size={17} /> : <Copy size={17} />}
            {copied ? 'QR içeriği kopyalandı' : 'QR içeriğini kopyala'}
          </button>
        )}
        <p className="qr-security-note">QR kodun siparişine özel olarak imzalanmıştır.</p>
      </section>
    </div>
  )
}

function CoffeeMark() {
  return <QrCode size={16} />
}
