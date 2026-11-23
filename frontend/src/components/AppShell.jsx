import {
  ArrowUpRight,
  Coffee,
  Crown,
  House,
  LogOut,
  ReceiptText,
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const navigation = [
  { to: '/', label: 'Ana sayfa', icon: House, end: true },
  { to: '/orders/history', label: 'Siparişlerim', icon: ReceiptText },
  { to: '/subscription', label: 'Aboneliğim', icon: Crown },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const initials = user?.full_name
    ?.split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toLocaleUpperCase('tr-TR')

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to="/" aria-label="KahveCell ana sayfa">
          <span className="brand-mark"><Coffee size={21} strokeWidth={2.5} /></span>
          <span>Kahve<span className="brand-light">Cell</span></span>
        </NavLink>

        <p className="nav-caption">MENÜ</p>
        <nav className="side-nav" aria-label="Ana navigasyon">
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-promo">
          <span className="promo-icon"><Crown size={18} /></span>
          <strong>Kahve keyfin<br />bir üst seviyede</strong>
          <span>Paketini keşfet, her yudumda avantaj kazan.</span>
          <NavLink to="/subscription">Paketleri gör <ArrowUpRight size={15} /></NavLink>
        </div>

        <button className="logout-button" onClick={handleLogout} type="button">
          <LogOut size={18} />
          <span>Çıkış yap</span>
        </button>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="mobile-brand">
            <span className="brand-mark"><Coffee size={19} strokeWidth={2.5} /></span>
            <span>Kahve<span className="brand-light">Cell</span></span>
          </div>
          <div className="topbar-note"><span className="online-dot" /> Kahve molan hazır</div>
          <div className="profile-chip">
            <span className="avatar">{initials || 'KC'}</span>
            <span className="profile-name">{user?.full_name || 'KahveCell üyesi'}</span>
          </div>
        </header>

        <main className="page-content"><Outlet /></main>
      </div>

      <nav className="mobile-nav" aria-label="Mobil navigasyon">
        {navigation.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `mobile-nav-link${isActive ? ' active' : ''}`}
          >
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
