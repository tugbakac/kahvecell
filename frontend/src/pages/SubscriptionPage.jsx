import { ArrowRight, Check, Crown, CreditCard, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, getErrorMessage } from '../api/client'

const planBenefits = {
  STARTER: ['Ayda 10 kahve hakkı', 'Tüm anlaşmalı dükkanlarda geçerli', 'İstediğin zaman iptal et'],
  PREMIUM: ['Ayda 20 kahve hakkı', '2 misafir kahve hakkı', 'Tüm anlaşmalı dükkanlarda geçerli'],
  UNLIMITED: ['Sınırsız kahve hakkı', '5 misafir kahve hakkı', 'Öncelikli servis avantajı'],
}

const planDescriptions = {
  STARTER: 'Kahve molalarını yeni keşfedenlere.',
  PREMIUM: 'Günün her anında kahve keyfi.',
  UNLIMITED: 'Kahve benim günlük ritüelim diyenlere.',
}

export default function SubscriptionPage() {
  const [plans, setPlans] = useState([])
  const [subscription, setSubscription] = useState(null)
  const [selectedPlan, setSelectedPlan] = useState('')
  const [cardNumber, setCardNumber] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([api.get('/subscriptions/plans'), api.get('/subscriptions/me')])
      .then(([plansResponse, subscriptionResponse]) => {
        if (!active) return
        const currentSubscription = subscriptionResponse.data.data
        setPlans(plansResponse.data.data)
        setSubscription(currentSubscription)
        setSelectedPlan(currentSubscription?.plan_type || 'STARTER')
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError, 'Abonelik bilgileri yüklenemedi.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  async function handlePayment(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setBusy(true)
    try {
      const payload = {
        plan_type: selectedPlan,
        card_number: cardNumber.replace(/[\s-]/g, ''),
      }
      const response = await api.request({
        method: subscription ? 'patch' : 'post',
        url: subscription ? '/subscriptions/me' : '/subscriptions',
        data: payload,
      })
      setSubscription(response.data.data.subscription)
      setCardNumber('')
      setNotice(subscription ? 'Paketin başarıyla güncellendi.' : 'Aboneliğin başarıyla başlatıldı.')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Ödeme tamamlanamadı.'))
    } finally {
      setBusy(false)
    }
  }

  async function handleCancel() {
    setError('')
    setNotice('')
    setCancelling(true)
    try {
      await api.delete('/subscriptions/me')
      setSubscription(null)
      setNotice('Aboneliğin iptal edildi.')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Abonelik iptal edilemedi.'))
    } finally {
      setCancelling(false)
    }
  }

  const selectedPlanData = plans.find((plan) => plan.plan_type === selectedPlan)
  const hasPlanChange = subscription && selectedPlan === subscription.plan_type

  return (
    <div className="page-stack narrow-page">
      <div className="page-title-block">
        <span className="eyebrow">KAHVENİN KEYFİ ABONELİKLE GÜZEL</span>
        <h1>Aboneliğin</h1>
        <p>Sana en uygun paketi seç, kahve molan hep yanında olsun.</p>
      </div>

      {error && <div className="inline-error" role="alert">{error}</div>}
      {notice && <div className="inline-success" role="status">{notice}</div>}

      {loading ? (
        <div className="loading-panel">Paketler yükleniyor…</div>
      ) : (
        <>
          {subscription && (
            <section className="current-subscription">
              <span className="current-plan-icon"><Crown size={21} /></span>
              <div>
                <span className="eyebrow">AKTİF PAKETİN</span>
                <h2>{subscription.plan_type} <span>· Aktif</span></h2>
                <p>
                  {subscription.remaining_credits == null
                    ? 'Sınırsız kahve hakkın var.'
                    : `${subscription.remaining_credits} / ${subscription.monthly_credit_limit} kahve hakkın kaldı.`}
                  {subscription.expires_at && ` Yenileme tarihi: ${new Date(`${subscription.expires_at}Z`).toLocaleDateString('tr-TR')}`}
                </p>
              </div>
              <Sparkles className="subscription-sparkle" size={23} />
            </section>
          )}

          <div className="plan-grid">
            {plans.map((plan) => (
              <button
                type="button"
                key={plan.plan_type}
                className={`plan-card${selectedPlan === plan.plan_type ? ' selected' : ''}${plan.plan_type === 'PREMIUM' ? ' plan-featured' : ''}`}
                onClick={() => setSelectedPlan(plan.plan_type)}
                aria-pressed={selectedPlan === plan.plan_type}
              >
                {plan.plan_type === 'PREMIUM' && <span className="plan-ribbon">EN ÇOK TERCİH EDİLEN</span>}
                <span className="plan-name">{plan.name}</span>
                <span className="plan-description">{planDescriptions[plan.plan_type]}</span>
                <span className="plan-price">
                  <strong>{plan.monthly_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</strong>
                  <span>₺ / ay</span>
                </span>
                <span className="plan-coffee-count">
                  <span className="plan-coffee-icon"><Crown size={16} /></span>
                  {plan.monthly_coffee_credits == null
                    ? 'Sınırsız kahve'
                    : `Ayda ${plan.monthly_coffee_credits} kahve`}
                </span>
                <span className="plan-benefit-list">
                  {planBenefits[plan.plan_type].map((benefit) => (
                    <span key={benefit}><Check size={15} /> {benefit}</span>
                  ))}
                </span>
                <span className="plan-select-indicator">
                  {selectedPlan === plan.plan_type ? 'Seçili paket' : 'Paketi seç'}
                </span>
              </button>
            ))}
          </div>

          <form className="payment-card" onSubmit={handlePayment}>
            <div className="payment-heading">
              <span className="payment-icon"><CreditCard size={19} /></span>
              <div>
                <h2>{subscription ? 'Paketini güncelle' : 'Aboneliğini başlat'}</h2>
                <p>Güvenli test ödemesi · Kart bilgileri saklanmaz</p>
              </div>
            </div>
            <label htmlFor="card-number">Test kart numarası</label>
            <input
              id="card-number"
              inputMode="numeric"
              autoComplete="cc-number"
              placeholder="4242 4242 4242 4242"
              value={cardNumber}
              onChange={(event) => setCardNumber(event.target.value.replace(/[^\d -]/g, '').slice(0, 19))}
              required
            />
            <p className="field-hint">Başarılı test: 4242 4242 4242 4242 · Başarısız test: 4000 0000 0000 0002</p>
            <div className="payment-summary">
              <span>{selectedPlanData?.name || 'Paket'} · 30 gün</span>
              <strong>{selectedPlanData ? `${selectedPlanData.monthly_price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺` : '—'}</strong>
            </div>
            <button
              className="button button-primary button-wide"
              type="submit"
              disabled={busy || !selectedPlan || hasPlanChange}
            >
              {busy ? 'İşlem yapılıyor…' : subscription ? 'Paketi güncelle' : 'Test kartıyla satın al'}
              {!busy && <ArrowRight size={17} />}
            </button>
          </form>

          {subscription && (
            <button
              className="cancel-subscription"
              type="button"
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? 'İptal ediliyor…' : 'Aboneliği iptal et'}
            </button>
          )}
        </>
      )}
    </div>
  )
}
