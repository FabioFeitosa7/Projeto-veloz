import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import StatusMessage from '../components/StatusMessage.jsx'
import { fechamentosApi } from '../services/api.js'

function mes(referencia) {
  return new Date(`${referencia}T12:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
}

function statusDoFechamento(status) {
  return { FINALIZADO: 'Finalizado', RASCUNHO: 'Rascunho', CANCELADO: 'Cancelado' }[status] || status
}

export default function HistoryPage() {
  const [recarregar, setRecarregar] = useState(0)
  const [estado, setEstado] = useState({ carregando: true, dados: [], erro: '' })

  useEffect(() => {
    const controller = new AbortController()
    fechamentosApi.listar({ signal: controller.signal })
      .then((dados) => setEstado({ carregando: false, dados, erro: '' }))
      .catch((erro) => { if (erro.name !== 'AbortError') setEstado({ carregando: false, dados: [], erro: erro.message }) })
    return () => controller.abort()
  }, [recarregar])

  return (
    <section>
      <div className="page-heading"><div><span className="eyebrow">Acompanhamento</span><h1>Histórico mensal</h1></div><Link className="button button-primary" to="/fechamentos/novo">Novo fechamento</Link></div>
      <div className="panel">
        {estado.carregando ? <StatusMessage>Carregando histórico…</StatusMessage> : estado.erro ? <StatusMessage tipo="erro" onRetry={() => setRecarregar((valor) => valor + 1)}>{estado.erro}</StatusMessage> : estado.dados.length === 0 ? <StatusMessage>Nenhum fechamento foi criado ainda.</StatusMessage> : (
          <div className="table-wrap"><table className="responsive-table">
            <thead><tr><th>Mês</th><th>Situação</th><th>Ingredientes</th><th>Itens para comprar</th><th><span className="sr-only">Ações</span></th></tr></thead>
            <tbody>{estado.dados.map((item) => <tr key={item.id}>
              <td className="mobile-primary" data-label="Mês"><Link className="table-link capitalize" to={`/historico/${item.id}`}>{mes(item.referencia)}</Link></td>
              <td data-label="Situação"><span className={`badge status-${item.status.toLowerCase()}`}>{statusDoFechamento(item.status)}</span></td>
              <td data-label="Ingredientes">{item.total_itens ?? item.itens.length}</td>
              <td data-label="Itens para comprar">{item.status === 'FINALIZADO' ? (item.total_compras ?? item.itens.filter((i) => Number(i.quantidade_compra) > 0).length) : '—'}</td>
              <td className="mobile-action" data-label="Ações"><Link className="text-link" to={item.status === 'RASCUNHO' ? `/fechamentos/${item.id}/editar` : `/historico/${item.id}`}>{item.status === 'RASCUNHO' ? 'Continuar' : 'Ver detalhes'}</Link></td>
            </tr>)}</tbody>
          </table></div>
        )}
      </div>
    </section>
  )
}
