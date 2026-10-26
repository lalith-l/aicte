import { useEffect, useState, type ReactNode } from 'react'
import SyntheticBanner from './components/SyntheticBanner'
import NavSidebar from './components/NavSidebar'
import DemoDrawer from './components/DemoDrawer'
import Login from './pages/Login'
import ApplicationList from './pages/ApplicationList'
import Dossier from './pages/Dossier'
import ReviewQueue from './pages/ReviewQueue'
import Alerts from './pages/Alerts'
import AuditorView from './pages/AuditorView'
import RulesAdmin from './pages/RulesAdmin'
import InstitutionPortal from './pages/InstitutionPortal'
import HeadHashFooter from './components/HeadHashFooter'
import { clearToken, getStoredRole, getToken } from './api/client'

function currentHashPath(): string {
  const raw = window.location.hash.replace(/^#/, '') || '/login'
  return raw.startsWith('/') ? raw : `/${raw}`
}

export default function App() {
  const [path, setPath] = useState(currentHashPath)
  const [username, setUsername] = useState(localStorage.getItem('aicte_username') || '')
  const [role, setRole] = useState(getStoredRole() || '')

  useEffect(() => {
    const onHash = () => setPath(currentHashPath())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  function navigate(to: string) {
    window.location.hash = to.startsWith('#') ? to : `#${to}`
  }

  function onLogin(user: string, nextRole: string) {
    localStorage.setItem('aicte_username', user)
    setUsername(user)
    setRole(nextRole)
    if (nextRole === 'institution_user') {
      navigate('/portal')
    } else if (nextRole === 'auditor') {
      navigate('/auditor')
    } else if (nextRole === 'rules_admin') {
      navigate('/rules')
    } else if (nextRole === 'sysadmin') {
      navigate('/auditor')
    } else {
      navigate('/applications')
    }
  }

  function onLogout() {
    clearToken()
    localStorage.removeItem('aicte_username')
    setUsername('')
    setRole('')
    navigate('/login')
  }

  const authed = Boolean(getToken() && role)
  const showLogin = !authed || path === '/login'

  if (showLogin) {
    return (
      <div>
        <SyntheticBanner />
        <Login onLogin={onLogin} />
      </div>
    )
  }

  let page: ReactNode
  if (path.startsWith('/applications/') && path !== '/applications/') {
    const appId = path.split('/')[2]
    page = <Dossier appId={appId} navigate={navigate} />
  } else if (path.startsWith('/review-queue')) {
    page = <ReviewQueue navigate={navigate} />
  } else if (path.startsWith('/alerts')) {
    page = <Alerts />
  } else if (path.startsWith('/auditor')) {
    page = <AuditorView />
  } else if (path.startsWith('/rules')) {
    page = <RulesAdmin />
  } else if (path.startsWith('/portal')) {
    page = <InstitutionPortal />
  } else if (path.startsWith('/applications')) {
    page = <ApplicationList navigate={navigate} />
  } else {
    // Role-based landing fallback
    if (role === 'institution_user') {
      page = <InstitutionPortal />
    } else if (role === 'auditor' || role === 'sysadmin') {
      page = <AuditorView />
    } else if (role === 'rules_admin') {
      page = <RulesAdmin />
    } else {
      page = <ApplicationList navigate={navigate} />
    }
  }

  return (
    <div className="app-layout">
      <div className="app-layout__banner">
        <SyntheticBanner />
      </div>
      <NavSidebar currentPath={path} role={role} username={username} onLogout={onLogout} />
      <div className="app-layout__content">
        {page}
        <HeadHashFooter />
      </div>
      <DemoDrawer onRolePreview={(r) => setRole(r)} />
    </div>
  )
}
