import { ArrowLeft, ArrowRight, Coffee, ShieldCheck, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function AuthPage({ mode = 'login' }) {
  const isRegister = mode === 'register'
  const location = useLocation()
  const navigate = useNavigate()
  const { requestOtp, verifyOtp, saveUser } = useAuth()
  const [step, setStep] = useState('phone')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [fullName, setFullName] = useState('')
  const [demoCode, setDemoCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const returnTo = location.state?.from?.pathname || '/'

  async function handleRequestOtp(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const digits = phone.replace(/\D/g, '')
      const nationalNumber = digits.length > 10 && digits.startsWith('90')
        ? digits.slice(2)
        : digits.startsWith('0')
          ? digits.slice(1)
          : digits
      const result = await requestOtp(`+90${nationalNumber}`)
      setPhone(result.phone_number)
      setDemoCode(result.otp_code)
      setStep('otp')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Doğrulama kodu alınamadı.'))
    } finally {
      setBusy(false)
    }
  }

  async function handleVerifyOtp(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const user = await verifyOtp(phone, otp)
      if (!user.profile_completed) {
        setStep('profile')
      } else {
        navigate(returnTo, { replace: true })
      }
    } catch (verifyError) {
      setError(getErrorMessage(verifyError, 'Kod doğrulanamadı.'))
    } finally {
      setBusy(false)
    }
  }

  async function handleCompleteProfile(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const response = await api.patch('/auth/me', { full_name: fullName })
      saveUser(response.data.data)
      navigate(returnTo, { replace: true })
    } catch (profileError) {
      setError(getErrorMessage(profileError, 'Profil kaydedilemedi.'))
    } finally {
      setBusy(false)
    }
  }

  function goBack() {
    setError('')
    setStep(step === 'profile' ? 'otp' : 'phone')
  }

  return (
    <main className="auth-page">
      <section className="auth-story">
        <Link className="brand auth-brand" to="/">
          <span className="brand-mark"><Coffee size={21} strokeWidth={2.5} /></span>
          <span>Kahve<span className="brand-light">Cell</span></span>
        </Link>
        <div className="auth-story-copy">
          <span className="eyebrow"><Sparkles size={14} /> GÜNÜN EN GÜZEL MOLASI</span>
          <h1>Kahveni seç.<br /><span>Molana değer kat.</span></h1>
          <p>Tek üyelikle şehrin sevilen kahvecileri, ayrıcalıklı paketler ve hızlı teslim.</p>
        </div>
        <div className="auth-story-footer">
          <span className="story-shield"><ShieldCheck size={18} /></span>
          Güvenli giriş · SMS kodu simülasyonu
        </div>
        <div className="auth-orbit orbit-one" />
        <div className="auth-orbit orbit-two" />
        <div className="auth-bean bean-one" />
        <div className="auth-bean bean-two" />
      </section>

      <section className="auth-form-side">
        <div className="auth-card">
          {step !== 'phone' && (
            <button className="back-button" type="button" onClick={goBack}>
              <ArrowLeft size={17} /> Geri dön
            </button>
          )}

          {step === 'phone' && (
            <>
              <span className="auth-step">01 / GSM NUMARASI</span>
              <h2>{isRegister ? 'Aramıza katıl' : 'Tekrar hoş geldin'}</h2>
              <p className="auth-description">
                {isRegister
                  ? 'Telefon numaranı doğrula, kahve ayrıcalıklarını keşfet.'
                  : 'Devam etmek için telefon numaranı doğrula.'}
              </p>
              <form className="auth-form" onSubmit={handleRequestOtp}>
                <label htmlFor="phone">GSM numarası</label>
                <div className="input-with-prefix">
                  <span>+90</span>
                  <input
                    id="phone"
                    autoComplete="tel"
                    inputMode="tel"
                    placeholder="5XX XXX XX XX"
                    value={phone.replace(/^\+90/, '')}
                    onChange={(event) => setPhone(event.target.value.replace(/\D/g, ''))}
                    required
                  />
                </div>
                <p className="field-hint">Numaran yalnızca giriş ve hesap güvenliği için kullanılır.</p>
                {!isRegister && (
                  <button
                    className="demo-code demo-phone"
                    type="button"
                    onClick={() => setPhone('5550000001')}
                  >
                    <ShieldCheck size={16} />
                    <span>Demo telefon numarası: <strong>+905550000001</strong></span>
                    <span className="demo-phone-action">Doldur</span>
                  </button>
                )}
                {error && <div className="form-error" role="alert">{error}</div>}
                <button className="button button-primary button-wide" disabled={busy} type="submit">
                  {busy ? 'Gönderiliyor…' : 'Doğrulama kodu gönder'}
                  {!busy && <ArrowRight size={17} />}
                </button>
              </form>
              <p className="auth-switch">
                {isRegister ? 'Zaten hesabın var mı?' : 'KahveCell’e yeni misin?'}{' '}
                <Link to={isRegister ? '/login' : '/register'}>
                  {isRegister ? 'Giriş yap' : 'Hesap oluştur'}
                </Link>
              </p>
            </>
          )}

          {step === 'otp' && (
            <>
              <span className="auth-step">02 / NUMARANI DOĞRULA</span>
              <h2>Kodunu gir</h2>
              <p className="auth-description">
                <strong>{phone}</strong> numarası için doğrulama kodunu gir.
              </p>
              <form className="auth-form" onSubmit={handleVerifyOtp}>
                <label htmlFor="otp">4 haneli doğrulama kodu</label>
                <input
                  className="otp-input"
                  id="otp"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={4}
                  placeholder="••••"
                  value={otp}
                  onChange={(event) => setOtp(event.target.value.replace(/\D/g, ''))}
                  required
                />
                {demoCode && (
                  <div className="demo-code">
                    <ShieldCheck size={16} />
                    Test SMS kodu: <strong>{demoCode}</strong>
                  </div>
                )}
                {error && <div className="form-error" role="alert">{error}</div>}
                <button className="button button-primary button-wide" disabled={busy} type="submit">
                  {busy ? 'Doğrulanıyor…' : 'Devam et'}
                  {!busy && <ArrowRight size={17} />}
                </button>
              </form>
            </>
          )}

          {step === 'profile' && (
            <>
              <span className="auth-step">03 / PROFİLİNİ TAMAMLA</span>
              <h2>Seni tanıyalım</h2>
              <p className="auth-description">Siparişlerini kişiselleştirmek için adını ekle.</p>
              <form className="auth-form" onSubmit={handleCompleteProfile}>
                <label htmlFor="full-name">Ad soyad</label>
                <input
                  id="full-name"
                  autoComplete="name"
                  placeholder="Adın ve soyadın"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  required
                />
                {error && <div className="form-error" role="alert">{error}</div>}
                <button className="button button-primary button-wide" disabled={busy} type="submit">
                  {busy ? 'Kaydediliyor…' : 'Profili tamamla'}
                  {!busy && <ArrowRight size={17} />}
                </button>
              </form>
            </>
          )}
        </div>
        <span className="auth-legal">Devam ederek kullanım koşullarını kabul etmiş olursun.</span>
      </section>
    </main>
  )
}
