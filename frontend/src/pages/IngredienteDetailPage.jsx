import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import IngredientStatus from '../components/IngredientStatus.jsx'
import StatusMessage from '../components/StatusMessage.jsx'
import { ingredientesApi } from '../services/api.js'

export default function IngredienteDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [estado, setEstado] = useState({ carregando: true, item: null, erro: '', alterando: false })

  useEffect(() => {
    const controller = new AbortController()
    ingredientesApi.obter(id, { signal: controller.signal })
      .then((item) => setEstado({ carregando: false, item, erro: '', alterando: false }))
      .catch((erro) => { if (erro.name !== 'AbortError') setEstado({ carregando: false, item: null, erro: erro.message, alterando: false }) })
    return () => controller.abort()
  }, [id])

  async function alternarSituacao() {
    const acao = estado.item.ativo ? 'desativar' : 'reativar'
    if (estado.item.ativo && !window.confirm(`Desativar o ingrediente ${estado.item.nome}?`)) return
    setEstado((atual) => ({ ...atual, alterando: true, erro: '' }))
    try {
      const item = await ingredientesApi[acao](id)
      setEstado({ carregando: false, item, erro: '', alterando: false })
    } catch (erro) {
      setEstado((atual) => ({ ...atual, alterando: false, erro: erro.message }))
    }
  }

  if (estado.carregando) return <StatusMessage>Carregando ingrediente…</StatusMessage>
  if (!estado.item) return <StatusMessage tipo="erro" onRetry={() => navigate('/ingredientes')}>{estado.erro || 'Ingrediente não encontrado.'}</StatusMessage>
  const item = estado.item
  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Ingredientes</span><h1>{item.nome}</h1></div><div className="heading-actions"><Link className="button button-secondary" to="/ingredientes">Voltar</Link><Link className="button button-primary" to={`/ingredientes/${id}/editar`}>Editar</Link></div></div>
      {location.state?.mensagem && <StatusMessage tipo="sucesso">{location.state.mensagem}</StatusMessage>}
      {estado.erro && <StatusMessage tipo="erro">{estado.erro}</StatusMessage>}
      <div className="panel detail-panel">
        <dl className="detail-grid">
          <div><dt>Situação</dt><dd>{item.ativo ? 'Ativo' : 'Inativo'}</dd></div>
          <div><dt>Unidade</dt><dd>{item.unidade_exibicao}</dd></div>
          <div><dt>Meta mensal</dt><dd>{Number(item.meta_atual).toLocaleString('pt-BR')} {item.unidade_exibicao}</dd></div>
          <div><dt>Estoque atual</dt><dd>{Number(item.estoque_atual).toLocaleString('pt-BR')} {item.unidade_exibicao}</dd></div>
          <div><dt>Data de validade</dt><dd>{new Date(`${item.data_validade}T12:00:00`).toLocaleDateString('pt-BR')}</dd></div>
          <div><dt>Estado da validade</dt><dd><IngredientStatus validade={item.validade} /><small>{item.validade.descricao}</small></dd></div>
        </dl>
        <div className="danger-zone"><div><strong>{item.ativo ? 'Desativar ingrediente' : 'Reativar ingrediente'}</strong><p>{item.ativo ? 'Ele deixará de aparecer nos próximos fechamentos.' : 'Ele voltará a participar dos próximos fechamentos.'}</p></div><button className={`button ${item.ativo ? 'button-danger' : 'button-primary'}`} onClick={alternarSituacao} disabled={estado.alterando}>{estado.alterando ? 'Aguarde…' : item.ativo ? 'Desativar' : 'Reativar'}</button></div>
      </div>
    </section>
  )
}
