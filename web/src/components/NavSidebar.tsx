import type { UserRole } from '../types'

interface NavItem {
  path: string
  label: string
  icon: string
  roles?: UserRole[]
}

const NAV_ITEMS: NavItem[] = [
  { path: '#/applications', label: 'Applications', icon: '📋', roles: ['scrutiny_officer', 'supervisor'] },
  { path: '#/review-queue', label: 'Review Queue', icon: '🔍', roles: ['scrutiny_officer', 'supervisor'] },
  { path: '#/alerts', label: 'Alerts', icon: '🔔', roles: ['scrutiny_officer', 'supervisor', 'auditor'] },
  { path: '#/auditor', label: 'Auditor View', icon: '🔒', roles: ['auditor'] },
  { path: '#/rules', label: 'Rules Admin', icon: '📐', roles: ['rules_admin'] },
  { path: '#/portal', label: 'Institution Portal', icon: '🏛', roles: ['institution_user'] },
  { path: '#/auditor', label: 'System Health', icon: '🖥', roles: ['sysadmin'] },
]

interface Props {
  currentPath: string
  role: string
  username: string
  onLogout: () => void
}

export default function NavSidebar({ currentPath, role, username, onLogout }: Props) {
  const isActive = (path: string) => currentPath.startsWith(path.replace('#', ''))

  const visibleItems = NAV_ITEMS.filter(item =>
    !item.roles || item.roles.includes(role as UserRole)
  )

  return (
    <div className="app-layout__sidebar">
      {/* Logo */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
          AICTE Validator
        </div>
        <div style={{ fontSize: 10, color: 'var(--amber)', marginTop: 2, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          Synthetic Data Prototype
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {visibleItems.map(item => (
          <a
            key={item.path}
            href={item.path}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 12px',
              borderRadius: 'var(--radius-sm)',
              textDecoration: 'none',
              color: isActive(item.path) ? 'var(--text-primary)' : 'var(--text-secondary)',
              background: isActive(item.path) ? 'rgba(59,130,246,0.12)' : 'transparent',
              borderLeft: isActive(item.path) ? '2px solid var(--blue)' : '2px solid transparent',
              fontSize: 13,
              fontWeight: isActive(item.path) ? 600 : 400,
              transition: 'all 0.15s',
            }}
          >
            <span style={{ fontSize: 15 }}>{item.icon}</span>
            {item.label}
          </a>
        ))}
      </nav>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* User info */}
      <div style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Logged in as</div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{username}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
          {role.replace(/_/g, ' ')}
        </div>
        <button className="btn" style={{ marginTop: 10, width: '100%', fontSize: 12 }} onClick={onLogout}>
          Sign Out
        </button>
      </div>
    </div>
  )
}
