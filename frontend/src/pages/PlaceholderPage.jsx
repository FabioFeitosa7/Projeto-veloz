import { Link } from 'react-router-dom'

export default function PlaceholderPage({ titulo }) {
  return (
    <section className="panel placeholder">
      <span className="eyebrow">Navegação</span>
      <h1>{titulo}</h1>
      <p>O endereço informado não existe ou não está mais disponível.</p>
      <Link className="button button-primary" to="/">Voltar ao painel</Link>
    </section>
  )
}
