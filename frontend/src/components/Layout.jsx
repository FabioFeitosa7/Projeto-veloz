import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const links = [
  ['/', 'Painel'],
  ['/ingredientes', 'Ingredientes'],
  ['/fechamentos/novo', 'Fechamento'],
  ['/historico', 'Histórico'],
]

export default function Layout() {
  const [menuAberto, setMenuAberto] = useState(false)

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/" aria-label="Estoque Veloz — início" onClick={() => setMenuAberto(false)}>
          <span className="brand-mark" aria-hidden="true">EV</span>
          <span>Estoque Veloz</span>
        </NavLink>
        <button
          className="menu-toggle"
          type="button"
          aria-expanded={menuAberto}
          aria-controls="navegacao-principal"
          onClick={() => setMenuAberto((aberto) => !aberto)}
        >
          <span className="menu-icon" aria-hidden="true"><i /><i /><i /></span>
          <span>{menuAberto ? 'Fechar' : 'Menu'}</span>
        </button>
        <nav id="navegacao-principal" className={menuAberto ? 'nav-open' : ''} aria-label="Navegação principal">
          {links.map(([destino, texto]) => (
            <NavLink key={destino} to={destino} end={destino === '/'} onClick={() => setMenuAberto(false)}>
              {texto}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="content"><Outlet /></main>
      <footer>Controle mensal de estoque</footer>
    </div>
  )
}
